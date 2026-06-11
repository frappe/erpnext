# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# License: GNU General Public License v3. See license.txt

"""Quarantine actions: mint Quality Control Lots when stock lands in a Quality Control warehouse.

This is deliberately route-agnostic — it reacts to a positive movement into a
Quality warehouse rather than re-resolving the trigger, so it works no matter how
the stock got there (receipt, transfer, redirect).
"""

import frappe
from frappe import _
from frappe.utils import flt

from erpnext.stock.services.quality_trigger_resolution import (
	INBOUND,
	OUTBOUND,
	movements_of,
	resolve_inspection_points,
)
from erpnext.stock.services.quality_warehouse import get_quality_warehouse, is_quality_warehouse


def apply_quarantine_routing(doc):
	"""Redirect Quarantine-triggered inbound rows into the Quality Control warehouse.

	Runs at validate time so the document still submits freely — the gate is on
	the stock (quarantined in the Quality Control warehouse until released), not
	on the document. Rows already pointed at a Quality Control warehouse are left
	alone, which also makes the routing idempotent across repeated validations.
	"""
	target_fieldname = "t_warehouse" if doc.doctype == "Stock Entry" else "warehouse"

	for point in resolve_inspection_points(doc):
		if point.quality_control_mode != "Quarantine" or point.role != INBOUND:
			continue
		if is_quality_warehouse(point.warehouse):
			continue

		quality_warehouse = get_quality_warehouse(point.warehouse)
		if not quality_warehouse:
			frappe.throw(
				_(
					"Row #{0}: Item {1} requires quarantine for quality inspection, but warehouse {2} "
					"has no Quality Control Warehouse configured."
				).format(point.row.idx, frappe.bold(point.item_code), frappe.bold(point.warehouse)),
				title=_("Quality Control Warehouse Missing"),
			)

		point.row.set(target_fieldname, quality_warehouse)
		_redirect_draft_bundle(point.row, quality_warehouse)
		frappe.msgprint(
			_("Row #{0}: Item {1} is routed to {2} for quality inspection.").format(
				point.row.idx, frappe.bold(point.item_code), frappe.bold(quality_warehouse)
			),
			alert=True,
		)


def _redirect_draft_bundle(row, quality_warehouse):
	"""A draft Serial and Batch Bundle built before routing still points at the
	original warehouse — carry it along, or its validation rightly refuses."""
	bundle = row.get("serial_and_batch_bundle")
	if not bundle:
		return

	info = frappe.db.get_value("Serial and Batch Bundle", bundle, ["docstatus", "warehouse"], as_dict=True)
	if not info or info.docstatus != 0 or info.warehouse == quality_warehouse:
		return

	frappe.db.set_value(
		"Serial and Batch Bundle", bundle, "warehouse", quality_warehouse, update_modified=False
	)
	frappe.db.sql(
		"""update `tabSerial and Batch Entry` set warehouse = %s where parent = %s""",
		(quality_warehouse, bundle),
	)


def validate_quality_warehouse_usage(doc):
	"""A Quality Control warehouse only receives stock that requires quarantine.

	Allowed inbound movements: those whose trigger resolves to Quarantine (the
	routed flow, or a direct receipt of a quarantine-triggered item) and items
	under a Periodic Re-test trigger (the scheduler's transfer). Anything else —
	parking ordinary stock in quarantine — is refused: it would sit locked behind
	the exit guard with no inspection path to release it.
	"""
	points = {(id(point.row), point.role): point for point in resolve_inspection_points(doc)}
	retest_items = {}

	for row, role, warehouse in movements_of(doc):
		if role != INBOUND or not is_quality_warehouse(warehouse):
			continue

		point = points.get((id(row), INBOUND))
		if point and point.quality_control_mode == "Quarantine":
			continue

		item_code = row.get("item_code")
		if item_code not in retest_items:
			from erpnext.stock.services.quality_retest import get_retest_trigger

			retest_items[item_code] = bool(get_retest_trigger(item_code))
		if retest_items[item_code]:
			continue

		frappe.throw(
			_(
				"Row #{0}: {1} is a Quality Control warehouse — it only receives stock that "
				"requires quarantine. Item {2} has no Quarantine trigger for this movement; "
				"receive it into a normal warehouse instead."
			).format(row.idx, frappe.bold(warehouse), frappe.bold(item_code)),
			title=_("Quality Control Warehouse"),
		)


def stamp_tracking_on_outward_row(
	row, *, item_code, warehouse, qty, company, batch_no=None, serial_nos=None, voucher_type="Stock Entry"
):
	"""Stamp batch / serial identity on a generated outward row, honouring Stock Settings.

	With use_serial_batch_fields enabled the legacy fields carry the (single)
	batch or the serial list; otherwise a Serial and Batch Bundle is created for
	the outward leg. Serial-tracked rows without an explicit list auto-pick.
	"""
	from frappe.utils import cint

	if not batch_no and not serial_nos:
		has_serial_no = frappe.get_cached_value("Item", item_code, "has_serial_no")
		if not has_serial_no:
			return row

	if cint(frappe.db.get_single_value("Stock Settings", "use_serial_batch_fields")):
		row["use_serial_batch_fields"] = 1
		if batch_no:
			row["batch_no"] = batch_no
		if serial_nos:
			row["serial_no"] = "\n".join(serial_nos)
		return row

	from erpnext.stock.serial_batch_bundle import SerialBatchCreation

	args = {
		"item_code": item_code,
		"warehouse": warehouse,
		"actual_qty": -flt(qty),
		"qty": -flt(qty),
		"type_of_transaction": "Outward",
		"voucher_type": voucher_type,
		"company": company,
		"do_not_submit": True,
	}
	if serial_nos:
		args["serial_nos"] = serial_nos
	if batch_no:
		args["batches"] = frappe._dict({batch_no: qty})

	bundle = SerialBatchCreation(args).make_serial_and_batch_bundle()
	if bundle.get("name"):
		row["serial_and_batch_bundle"] = bundle.name
	return row


def get_release_warehouse(quality_warehouse):
	"""The store warehouse to release accepted stock into.

	Resolved by reverse lookup: the warehouse whose quality_warehouse points at
	this Quality Control warehouse. Ambiguous (several stores sharing one Quality
	Control warehouse) resolves to None — the user releases manually and picks the
	target.
	"""
	stores = frappe.get_all(
		"Warehouse", filters={"quality_warehouse": quality_warehouse, "disabled": 0}, pluck="name"
	)
	return stores[0] if len(stores) == 1 else None


def process_inspection_result(doc, method=None):
	"""React to a submitted Quality Inspection that decides a Quality Control Lot.

	Sample basis: the inspection's overall status accepts or rejects the whole
	pending quantity. Each Quantity basis: the reading bundle's per-unit counts
	split it — accepted units are released, rejected units stay quarantined for
	the purchase return, and uninspected units remain pending.
	"""
	if doc.reference_type != "Quality Control Lot" or not doc.reference_name:
		return

	lot = frappe.get_doc("Quality Control Lot", doc.reference_name)
	pending_qty = flt(lot.pending_qty)
	if not pending_qty:
		return

	if lot.batch_no:
		from erpnext.stock.services.quality_retest import schedule_next_retest

		schedule_next_retest(lot.item_code, lot.batch_no)

	# the inspection's basis governs (the lot's is the fetched proposal, which
	# the inspector may override); a manual inspection decides the whole pending
	# quantity without per-unit readings
	if (
		doc.get("inspection_basis") == "Each Quantity"
		and not doc.get("reading_bundle")
		and not doc.get("manual_inspection")
	):
		frappe.throw(
			_(
				"This inspection is on an Each Quantity basis: every unit needs its own readings. "
				"Attach a Quality Inspection Reading Bundle before submitting, or check Manual "
				"Inspection to record an overriding verdict."
			),
			title=_("Per-Unit Readings Required"),
		)

	if doc.get("reading_bundle"):
		bundle = frappe.get_doc("Quality Inspection Reading Bundle", doc.reading_bundle)
		if bundle.docstatus != 1:
			frappe.throw(
				_(
					"Submit Reading Bundle {0} before submitting the inspection — its per-unit "
					"readings decide the lot and must be frozen first."
				).format(frappe.bold(bundle.name)),
				title=_("Reading Bundle Not Submitted"),
			)
		if bundle.item_code != lot.item_code:
			frappe.throw(
				_("Reading Bundle {0} is for item {1}, not the lot's item {2}.").format(
					frappe.bold(bundle.name), frappe.bold(bundle.item_code), frappe.bold(lot.item_code)
				)
			)
		accepted_qty = min(flt(bundle.accepted_qty), pending_qty)
		rejected_qty = min(flt(bundle.rejected_qty), pending_qty - accepted_qty)
	elif doc.status == "Rejected":
		accepted_qty, rejected_qty = 0.0, pending_qty
	else:
		accepted_qty, rejected_qty = pending_qty, 0.0

	if rejected_qty:
		lot.rejected_qty = flt(lot.rejected_qty) + rejected_qty
		lot.flags.ignore_permissions = True
		lot.save()

	if not accepted_qty:
		return

	release_warehouse = get_release_warehouse(lot.quality_warehouse)
	if not release_warehouse:
		frappe.msgprint(
			_(
				"Quality Control Lot {0} is accepted, but no unique release warehouse points at {1}. "
				"Create the Quality Control Release manually."
			).format(frappe.bold(lot.name), frappe.bold(lot.quality_warehouse)),
			alert=True,
		)
		return

	accepted_serials = None
	if doc.get("reading_bundle"):
		accepted_serials = (
			frappe.get_doc("Quality Inspection Reading Bundle", doc.reading_bundle).get_unit_serials(
				"Accepted"
			)
			or None
		)

	release = frappe.new_doc("Stock Entry")
	release.purpose = "Quality Control Release"
	release.stock_entry_type = "Quality Control Release"
	release.company = lot.company
	release.quality_control_lot = lot.name
	release_row = {
		"item_code": lot.item_code,
		"qty": accepted_qty,
		"s_warehouse": lot.quality_warehouse,
		"t_warehouse": release_warehouse,
	}
	stamp_tracking_on_outward_row(
		release_row,
		item_code=lot.item_code,
		warehouse=lot.quality_warehouse,
		qty=accepted_qty,
		company=lot.company,
		batch_no=lot.batch_no,
		serial_nos=accepted_serials,
	)
	release.append("items", release_row)
	release.flags.ignore_permissions = True
	release.insert()
	release.submit()

	frappe.msgprint(
		_("Quality Control Release {0} created: {1} released to {2}.").format(
			frappe.utils.get_link_to_form("Stock Entry", release.name),
			accepted_qty,
			frappe.bold(release_warehouse),
		),
		alert=True,
	)


@frappe.whitelist()
def make_purchase_return_for_lot(lot_name: str):
	"""A purchase return pre-filled with the lot's rejected quantity awaiting return.

	Built from the lot's source document, trimmed to the lot's item, with the
	quantity set to the rejected-outstanding units and the Quality Control
	warehouse as the source — the only stock a return may take out of quarantine.
	"""
	from erpnext.controllers.sales_and_purchase_return import make_return_doc

	lot = frappe.get_doc("Quality Control Lot", lot_name)

	if lot.source_document_type not in ("Purchase Receipt", "Purchase Invoice", "Subcontracting Receipt"):
		frappe.throw(
			_(
				"A purchase return applies only to lots sourced from a Purchase Receipt, Purchase "
				"Invoice or Subcontracting Receipt. Lot {0} came from {1}."
			).format(frappe.bold(lot.name), frappe.bold(lot.source_document_type))
		)

	outstanding = flt(lot.rejected_qty) - flt(lot.returned_qty) - flt(lot.disposed_qty)
	if outstanding <= 0:
		frappe.throw(
			_("Quality Control Lot {0} has no rejected quantity awaiting return.").format(
				frappe.bold(lot.name)
			)
		)

	return_doc = make_return_doc(lot.source_document_type, lot.source_document)
	rows = [
		row
		for row in return_doc.items
		if row.item_code == lot.item_code and row.get("warehouse") == lot.quality_warehouse
	]
	if not rows:
		frappe.throw(
			_("{0} has no returnable row for item {1} in {2}.").format(
				frappe.bold(lot.source_document),
				frappe.bold(lot.item_code),
				frappe.bold(lot.quality_warehouse),
			)
		)

	row = rows[0]
	return_doc.set("items", [row])
	row.qty = -outstanding
	if row.meta.has_field("received_qty"):
		row.received_qty = -outstanding

	# the return carries the lot's batch and exactly the rejected serials still
	# held in quarantine
	row.serial_and_batch_bundle = None
	row.batch_no = None
	row.serial_no = None
	tracking = stamp_tracking_on_outward_row(
		{},
		item_code=lot.item_code,
		warehouse=lot.quality_warehouse,
		qty=outstanding,
		company=lot.company,
		batch_no=lot.batch_no,
		serial_nos=_rejected_serials_awaiting_return(lot, outstanding),
		voucher_type=lot.source_document_type,
	)
	row.update(tracking)

	return return_doc


@frappe.whitelist()
def make_rejected_stock_transfer_for_lot(lot_name: str):
	"""A Quality Control Release moving the lot's rejected stock to a Rejected warehouse.

	The other disposition for rejected stock besides a purchase return: out of
	quarantine into a Rejected warehouse, where normal stock rules take over
	(scrap with a Material Issue, rework, sale as scrap). Pre-filled with the
	rejected quantity still in quarantine, the lot's batch and exactly the
	rejected serials; the target is resolved when the company has a single
	Rejected warehouse, otherwise the user picks it.
	"""
	lot = frappe.get_doc("Quality Control Lot", lot_name)

	outstanding = flt(lot.rejected_qty) - flt(lot.returned_qty) - flt(lot.disposed_qty)
	if outstanding <= 0:
		frappe.throw(
			_("Quality Control Lot {0} has no rejected quantity in quarantine.").format(
				frappe.bold(lot.name)
			)
		)

	rejected_warehouses = frappe.get_all(
		"Warehouse",
		filters={
			"warehouse_type": "Rejected",
			"company": lot.company,
			"is_group": 0,
			"disabled": 0,
		},
		pluck="name",
	)
	if not rejected_warehouses:
		frappe.throw(
			_(
				"No Rejected warehouse exists for {0}. Create a warehouse with type Rejected to "
				"move rejected stock out of quarantine."
			).format(frappe.bold(lot.company)),
			title=_("Rejected Warehouse Missing"),
		)

	entry = frappe.new_doc("Stock Entry")
	entry.purpose = "Quality Control Release"
	entry.stock_entry_type = "Quality Control Release"
	entry.company = lot.company
	entry.quality_control_lot = lot.name
	row = {
		"item_code": lot.item_code,
		"qty": outstanding,
		"s_warehouse": lot.quality_warehouse,
		"t_warehouse": rejected_warehouses[0] if len(rejected_warehouses) == 1 else None,
	}
	stamp_tracking_on_outward_row(
		row,
		item_code=lot.item_code,
		warehouse=lot.quality_warehouse,
		qty=outstanding,
		company=lot.company,
		batch_no=lot.batch_no,
		serial_nos=_rejected_serials_awaiting_return(lot, outstanding),
	)
	entry.append("items", row)
	return entry


def trim_return_to_rejected_outstanding(return_doc):
	"""Shape a purchase return around the quality verdicts.

	Rows drawing from a Quality Control warehouse are trimmed to the rejected
	quantity still awaiting return — with the lot's batch and the rejected
	serials stamped — and dropped entirely when nothing awaits return there
	(pending and accepted stock leaves quarantine through inspection, not
	returns). Rows from normal warehouses are untouched.
	"""
	kept = []
	touched = False
	for row in return_doc.items:
		warehouse = row.get("warehouse")
		if not warehouse or not is_quality_warehouse(warehouse):
			# Block flow: stock was never held, but the row's inspection still
			# knows what was rejected — prefill as an editable default
			_prefill_rejections_from_row_inspection(return_doc, row)
			kept.append(row)
			continue

		touched = True
		lots = frappe.get_all(
			"Quality Control Lot",
			filters={
				"source_document_type": return_doc.get("return_against") and return_doc.doctype,
				"source_document": return_doc.get("return_against"),
				"item_code": row.item_code,
				"quality_warehouse": warehouse,
			},
			fields=["name", "rejected_qty", "returned_qty", "disposed_qty"],
		)
		outstanding = sum(
			max(flt(lot.rejected_qty) - flt(lot.returned_qty) - flt(lot.disposed_qty), 0) for lot in lots
		)
		if outstanding <= 0:
			continue  # nothing awaits return from quarantine for this row

		row.qty = -outstanding
		if row.meta.has_field("received_qty"):
			row.received_qty = -outstanding

		row.serial_and_batch_bundle = None
		row.batch_no = None
		row.serial_no = None
		if len(lots) == 1:
			lot = frappe.get_doc("Quality Control Lot", lots[0].name)
			tracking = stamp_tracking_on_outward_row(
				{},
				item_code=lot.item_code,
				warehouse=warehouse,
				qty=outstanding,
				company=lot.company,
				batch_no=lot.batch_no,
				serial_nos=_rejected_serials_awaiting_return(lot, outstanding),
				voucher_type=return_doc.doctype,
			)
			row.update(tracking)
		kept.append(row)

	if touched and not kept:
		frappe.throw(
			_(
				"Nothing awaits return from quarantine: only rejected stock leaves with a purchase "
				"return. Pending stock needs its inspection decision, and accepted stock leaves "
				"with a Quality Control Release."
			),
			title=_("No Rejected Stock"),
		)

	if len(kept) != len(return_doc.items):
		return_doc.set("items", kept)
		for idx, row in enumerate(return_doc.items, start=1):
			row.idx = idx


def _prefill_rejections_from_row_inspection(return_doc, row):
	"""Best-effort prefill for Block-flow returns.

	Without quarantine there is no lot ledger or lock — the rejected units sit
	saleable in the store — so this only proposes a default: the inspection
	bundle's rejected count minus what prior returns already took, with the
	rejected serials still present in the warehouse. The row stays editable.
	"""
	source = getattr(return_doc, "_quality_source_doc", None)
	if source is None:
		source = frappe.get_doc(return_doc.doctype, return_doc.return_against)
		return_doc._quality_source_doc = source

	source_row = next(
		(
			r
			for r in source.items
			if r.item_code == row.item_code
			and r.get("warehouse") == row.get("warehouse")
			and r.get("quality_inspection")
		),
		None,
	)
	if not source_row:
		return

	inspection = frappe.db.get_value(
		"Quality Inspection",
		{"name": source_row.quality_inspection, "docstatus": 1},
		["name", "reading_bundle"],
		as_dict=True,
	)
	if not inspection or not inspection.reading_bundle:
		return

	bundle = frappe.get_doc("Quality Inspection Reading Bundle", inspection.reading_bundle)
	if not flt(bundle.rejected_qty):
		return

	prior_returns = frappe.get_all(
		return_doc.doctype,
		filters={"return_against": return_doc.return_against, "docstatus": 1},
		pluck="name",
	)
	already_returned = 0.0
	if prior_returns:
		already_returned = abs(
			flt(
				frappe.db.get_value(
					f"{return_doc.doctype} Item",
					{"parent": ("in", prior_returns), "item_code": row.item_code},
					"sum(qty)",
				)
			)
		)

	outstanding = min(flt(bundle.rejected_qty) - already_returned, abs(flt(row.qty)))
	if outstanding <= 0:
		return

	row.qty = -outstanding
	if row.meta.has_field("received_qty"):
		row.received_qty = -outstanding

	rejected_serials = [
		serial
		for serial in bundle.get_unit_serials("Rejected")
		if frappe.db.get_value("Serial No", serial, "warehouse") == row.get("warehouse")
	][: int(outstanding)]
	if rejected_serials:
		row.serial_and_batch_bundle = None
		row.serial_no = None
		tracking = stamp_tracking_on_outward_row(
			{},
			item_code=row.item_code,
			warehouse=row.get("warehouse"),
			qty=outstanding,
			company=source.company,
			batch_no=row.get("batch_no"),
			serial_nos=rejected_serials,
			voucher_type=return_doc.doctype,
		)
		row.update(tracking)


def _rejected_serials_awaiting_return(lot, outstanding):
	"""The rejected units' serials that are still in the Quality Control warehouse."""
	if not lot.quality_inspection:
		return None

	reading_bundle = frappe.db.get_value("Quality Inspection", lot.quality_inspection, "reading_bundle")
	if not reading_bundle:
		return None

	rejected = frappe.get_doc("Quality Inspection Reading Bundle", reading_bundle).get_unit_serials(
		"Rejected"
	)
	still_held = [
		serial
		for serial in rejected
		if frappe.db.get_value("Serial No", serial, "warehouse") == lot.quality_warehouse
	]
	return still_held[: int(outstanding)] or None


def sync_source_document_quality_status(source_doctype, source_name):
	"""Aggregate a document's lot statuses onto its Quality Status field."""
	if not source_doctype or not source_name:
		return
	if not frappe.get_meta(source_doctype).has_field("quality_status"):
		return

	statuses = set(
		frappe.get_all(
			"Quality Control Lot",
			filters={"source_document_type": source_doctype, "source_document": source_name},
			pluck="status",
		)
	)

	if "Under Inspection" in statuses:
		value = "Under Inspection"
	elif "Partially Released" in statuses:
		value = "Partially Released"
	elif statuses == {"Released"}:
		value = "Released"
	elif statuses == {"Rejected"}:
		value = "Rejected"
	elif statuses:
		value = "Inspection Completed"
	else:
		value = None

	frappe.db.set_value(source_doctype, source_name, "quality_status", value, update_modified=False)


def reverse_inspection_result(doc, method=None):
	"""Cancelling the deciding inspection unwinds its consequences on the lot.

	The Quality Control Releases it caused are cancelled (stock returns to
	quarantine, the release reverses the accepted quantity) and the rejected
	quantity it booked is cleared, so the lot is back under inspection in full.
	A purchase return already booked against the lot blocks the cancellation —
	unwind the return first, mirroring every other dependency chain here.
	"""
	if doc.reference_type != "Quality Control Lot" or not doc.reference_name:
		return
	if not frappe.db.exists("Quality Control Lot", doc.reference_name):
		return

	lot = frappe.get_doc("Quality Control Lot", doc.reference_name)

	if flt(lot.returned_qty):
		frappe.throw(
			_(
				"Cannot cancel: a purchase return is already booked against Quality Control Lot {0}. "
				"Unwind the return first."
			).format(frappe.bold(lot.name)),
			title=_("Purchase Return Booked"),
		)

	releases = frappe.get_all(
		"Stock Entry",
		filters={"quality_control_lot": lot.name, "docstatus": 1},
		pluck="name",
	)
	for name in releases:
		release = frappe.get_doc("Stock Entry", name)
		release.flags.ignore_permissions = True
		release.cancel()

	lot.reload()
	if flt(lot.rejected_qty):
		lot.rejected_qty = 0
		lot.flags.ignore_permissions = True
		lot.save()


def handle_source_document_cancel(doc, method=None):
	"""Cascade a source-document cancellation onto its Quality Control Lots.

	An untouched lot (nothing released or rejected yet) is deleted along with the
	reversed stock. A lot that already released or rejected quantity blocks the
	cancellation — the Quality Control Release or purchase return must be
	unwound first, mirroring how ERPNext blocks cancelling documents with
	downstream submitted documents.
	"""
	lots = frappe.get_all(
		"Quality Control Lot",
		filters={"source_document_type": doc.doctype, "source_document": doc.name},
		fields=["name", "accepted_qty", "rejected_qty"],
	)

	for lot in lots:
		if flt(lot.accepted_qty) or flt(lot.rejected_qty):
			frappe.throw(
				_(
					"Cannot cancel: Quality Control Lot {0} created by this document has already been "
					"released or rejected. Unwind the Quality Control Release or purchase return first."
				).format(frappe.bold(lot.name)),
				title=_("Quality Control Lot In Use"),
			)
		frappe.delete_doc("Quality Control Lot", lot.name, ignore_permissions=True)


def update_lots_for_purchase_return(doc, method=None):
	"""Book a purchase return out of a Quality Control warehouse against its lots.

	The return has no explicit lot link, so allocation is implicit: rows taking
	stock out of a Quality Control warehouse are matched to that item's lots with
	rejected quantity still awaiting return — batch matches first, then oldest
	first. A return larger than the rejected-outstanding quantity is refused,
	which also stops returns from smuggling accepted or pending stock out of
	quarantine. Cancelling the return books the allocation back.
	"""
	if doc.doctype not in (
		"Purchase Receipt",
		"Purchase Invoice",
		"Subcontracting Receipt",
	) or not doc.get("is_return"):
		return

	for row, role, warehouse in movements_of(doc):
		if role != OUTBOUND or not is_quality_warehouse(warehouse):
			continue

		return_qty = abs(flt(row.get("stock_qty")) or flt(row.get("qty")))
		if not return_qty:
			continue

		if method == "before_submit":
			# capacity is checked before anything persists, so a refused return
			# leaves no half-submitted state behind
			_validate_return_capacity(row, warehouse, return_qty)
		elif method == "on_cancel":
			_allocate_return_to_lots(row, warehouse, return_qty, -1)
		else:
			_allocate_return_to_lots(row, warehouse, return_qty, +1)


def _rejected_outstanding_lots(item_code, warehouse, batch_no=None):
	lots = frappe.get_all(
		"Quality Control Lot",
		filters={"item_code": item_code, "quality_warehouse": warehouse},
		fields=["name", "batch_no", "rejected_qty", "returned_qty", "disposed_qty"],
		order_by="creation",
	)
	# a return carrying a batch books only against that batch's lots — never
	# against a lot holding a different batch
	if batch_no:
		lots = [lot for lot in lots if not lot.batch_no or lot.batch_no == batch_no]
		lots.sort(key=lambda lot: 0 if lot.batch_no == batch_no else 1)
	return lots


def _validate_return_capacity(row, warehouse, return_qty):
	lots = _rejected_outstanding_lots(row.get("item_code"), warehouse, row.get("batch_no"))
	capacity = sum(
		flt(lot.rejected_qty) - flt(lot.returned_qty) - flt(lot.disposed_qty) for lot in lots
	)
	if return_qty > capacity:
		frappe.throw(
			_(
				"Row #{0}: Only {1} rejected unit(s) of {2} in {3} are awaiting return. Stock that "
				"is pending or accepted leaves quarantine through a Quality Control Release, not a "
				"purchase return."
			).format(row.idx, capacity, frappe.bold(row.get("item_code")), frappe.bold(warehouse)),
			title=_("Return Exceeds Rejected Stock"),
		)


def _allocate_return_to_lots(row, warehouse, return_qty, direction):
	remaining = return_qty
	for lot in _rejected_outstanding_lots(row.get("item_code"), warehouse, row.get("batch_no")):
		if remaining <= 0:
			break

		if direction > 0:
			capacity = flt(lot.rejected_qty) - flt(lot.returned_qty) - flt(lot.disposed_qty)
		else:
			capacity = flt(lot.returned_qty)
		if capacity <= 0:
			continue

		allocated = min(capacity, remaining)
		frappe.db.set_value(
			"Quality Control Lot",
			lot.name,
			"returned_qty",
			flt(lot.returned_qty) + direction * allocated,
			update_modified=False,
		)
		remaining -= allocated


def block_stock_reconciliation_on_quality_warehouse(doc, method=None):
	"""Stock Reconciliation may not touch a Quality Control warehouse.

	Reconciliation sets absolute quantities, which would silently desynchronise
	the warehouse balance from its Quality Control Lots. Quarantined stock only
	moves through controlled flows (release / return / cancellation).
	"""
	for row in doc.get("items") or []:
		if is_quality_warehouse(row.get("warehouse")):
			frappe.throw(
				_(
					"Row #{0}: {1} is a Quality Control warehouse. Stock Reconciliation is not "
					"allowed on quarantined stock."
				).format(row.idx, frappe.bold(row.warehouse)),
				title=_("Quality Control Warehouse"),
			)


def create_quality_control_lots(doc, method=None):
	"""Mint a Quality Control Lot for each item moving into a Quality warehouse on this document."""
	from erpnext.stock.services.quality_retest import get_retest_trigger

	points_by_row = {id(point.row): point for point in resolve_inspection_points(doc)}

	for row, role, warehouse in movements_of(doc):
		if role != INBOUND or not is_quality_warehouse(warehouse):
			continue

		# a customer return carries negative quantities; the lot records the
		# absolute quantity that physically entered the Quality Control warehouse
		received_qty = abs(flt(row.get("transfer_qty") or row.get("stock_qty") or row.get("qty")))
		if not received_qty:
			continue

		# one lot per batch: a row carrying several batches in its bundle splits,
		# so every lot keeps the batch guarantees (release, return, re-test)
		batch_qty_map = {}
		if row.get("batch_no"):
			batch_qty_map[row.batch_no] = received_qty
		elif row.get("serial_and_batch_bundle"):
			for entry in frappe.get_all(
				"Serial and Batch Entry",
				filters={"parent": row.serial_and_batch_bundle, "batch_no": ("is", "set")},
				fields=["batch_no", "qty"],
			):
				batch_qty_map[entry.batch_no] = batch_qty_map.get(entry.batch_no, 0) + abs(flt(entry.qty))
		if not batch_qty_map:
			batch_qty_map = {None: received_qty}

		# carry the inspection template/basis from the trigger that caused the
		# quarantine; periodic re-test transfers fall back to the re-test trigger
		point = points_by_row.get(id(row))
		template = point.inspection_template if point else None
		basis = point.inspection_basis if point else None
		if not template:
			retest_trigger = get_retest_trigger(row.get("item_code"))
			if retest_trigger:
				template = retest_trigger.inspection_template
				basis = retest_trigger.inspection_basis

		for batch_no, batch_qty in batch_qty_map.items():
			lot = frappe.get_doc(
				{
					"doctype": "Quality Control Lot",
					"item_code": row.get("item_code"),
					"company": doc.get("company"),
					"quality_warehouse": warehouse,
					"batch_no": batch_no,
					"received_qty": batch_qty,
					"source_document_type": doc.doctype,
					"source_document": doc.name,
					"inspection_template": template,
				}
			)
			if basis:
				lot.inspection_basis = basis
			lot.insert(ignore_permissions=True)
