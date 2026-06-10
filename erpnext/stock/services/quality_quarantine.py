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
		frappe.msgprint(
			_("Row #{0}: Item {1} is routed to {2} for quality inspection.").format(
				point.row.idx, frappe.bold(point.item_code), frappe.bold(quality_warehouse)
			),
			alert=True,
		)


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

	# a manual inspection is the inspector's overriding verdict: it decides the
	# whole pending quantity without per-unit readings
	if (
		lot.inspection_basis == "Each Quantity"
		and not doc.get("reading_bundle")
		and not doc.get("manual_inspection")
	):
		frappe.throw(
			_(
				"Quality Control Lot {0} is inspected on an Each Quantity basis: every unit needs "
				"its own readings. Attach a Quality Inspection Reading Bundle before submitting, "
				"or check Manual Inspection to record an overriding verdict."
			).format(frappe.bold(lot.name)),
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

	release = frappe.new_doc("Stock Entry")
	release.purpose = "Quality Control Release"
	release.stock_entry_type = "Quality Control Release"
	release.company = lot.company
	release.quality_control_lot = lot.name
	release.append(
		"items",
		{
			"item_code": lot.item_code,
			"qty": accepted_qty,
			"s_warehouse": lot.quality_warehouse,
			"t_warehouse": release_warehouse,
			"batch_no": lot.batch_no,
			"use_serial_batch_fields": 1 if lot.batch_no else 0,
		},
	)
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
	if doc.doctype not in ("Purchase Receipt", "Purchase Invoice") or not doc.get("is_return"):
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
		fields=["name", "batch_no", "rejected_qty", "returned_qty"],
		order_by="creation",
	)
	# prefer lots of the same batch, then first-in-first-out
	lots.sort(key=lambda lot: 0 if batch_no and lot.batch_no == batch_no else 1)
	return lots


def _validate_return_capacity(row, warehouse, return_qty):
	lots = _rejected_outstanding_lots(row.get("item_code"), warehouse, row.get("batch_no"))
	capacity = sum(flt(lot.rejected_qty) - flt(lot.returned_qty) for lot in lots)
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
			capacity = flt(lot.rejected_qty) - flt(lot.returned_qty)
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

		received_qty = row.get("transfer_qty") or row.get("stock_qty") or row.get("qty")
		if not received_qty:
			continue

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

		lot = frappe.get_doc(
			{
				"doctype": "Quality Control Lot",
				"item_code": row.get("item_code"),
				"company": doc.get("company"),
				"quality_warehouse": warehouse,
				"batch_no": row.get("batch_no"),
				"received_qty": received_qty,
				"source_document_type": doc.doctype,
				"source_document": doc.name,
				"inspection_template": template,
			}
		)
		if basis:
			lot.inspection_basis = basis
		lot.insert(ignore_permissions=True)
