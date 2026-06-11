# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# License: GNU General Public License v3. See license.txt

"""Purchase returns of rejected quarantined stock.

A return out of a Quality Control warehouse books against the lots its receipt
minted — capacity-checked before submission, allocated on submission, given
back on cancellation — and returns built from a lot or a receipt are trimmed
and pre-filled with the rejected units still held.
"""

import frappe
from frappe import _
from frappe.utils import flt

from erpnext.stock.services.quality_quarantine import stamp_tracking_on_outward_row
from erpnext.stock.services.quality_release import _rejected_serials_awaiting_return
from erpnext.stock.services.quality_trigger_resolution import OUTBOUND, movements_of
from erpnext.stock.services.quality_warehouse import is_quality_warehouse


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

	# a return gives back the receipt's own stock: book against the lots that
	# receipt minted, never against another lot of the same item that happens
	# to share the Quality Control warehouse
	source = (doc.doctype, doc.return_against) if doc.get("return_against") else None

	for row, role, warehouse in movements_of(doc):
		if role != OUTBOUND or not is_quality_warehouse(warehouse):
			continue

		return_qty = abs(flt(row.get("stock_qty")) or flt(row.get("qty")))
		if not return_qty:
			continue

		if method == "before_submit":
			# capacity is checked before anything persists, so a refused return
			# leaves no half-submitted state behind
			_validate_return_capacity(row, warehouse, return_qty, source)
		elif method == "on_cancel":
			_allocate_return_to_lots(row, warehouse, return_qty, -1, source)
		else:
			_allocate_return_to_lots(row, warehouse, return_qty, +1, source)


def _rejected_outstanding_lots(item_code, warehouse, batch_no=None, source=None):
	filters = {"item_code": item_code, "quality_warehouse": warehouse}
	if source:
		filters["source_document_type"], filters["source_document"] = source
	lots = frappe.get_all(
		"Quality Control Lot",
		filters=filters,
		fields=["name", "batch_no", "rejected_qty", "returned_qty", "disposed_qty"],
		order_by="creation",
	)
	# a return carrying a batch books only against that batch's lots — never
	# against a lot holding a different batch
	if batch_no:
		lots = [lot for lot in lots if not lot.batch_no or lot.batch_no == batch_no]
		lots.sort(key=lambda lot: 0 if lot.batch_no == batch_no else 1)
	return lots


def _validate_return_capacity(row, warehouse, return_qty, source=None):
	lots = _rejected_outstanding_lots(row.get("item_code"), warehouse, row.get("batch_no"), source)
	capacity = sum(flt(lot.rejected_qty) - flt(lot.returned_qty) - flt(lot.disposed_qty) for lot in lots)
	if return_qty > capacity:
		frappe.throw(
			_(
				"Row #{0}: Only {1} rejected unit(s) of {2} in {3} are awaiting return. Stock that "
				"is pending or accepted leaves quarantine through a Quality Control Release, not a "
				"purchase return."
			).format(row.idx, capacity, frappe.bold(row.get("item_code")), frappe.bold(warehouse)),
			title=_("Return Exceeds Rejected Stock"),
		)


def _allocate_return_to_lots(row, warehouse, return_qty, direction, source=None):
	remaining = return_qty
	for lot in _rejected_outstanding_lots(row.get("item_code"), warehouse, row.get("batch_no"), source):
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


@frappe.whitelist()
def make_purchase_return_for_lot(lot_name: str):
	"""A purchase return pre-filled with the lot's rejected quantity awaiting return.

	Built from the lot's source document, trimmed to the lot's item, with the
	quantity set to the rejected-outstanding units and the Quality Control
	warehouse as the source — the only stock a return may take out of quarantine.
	"""
	from erpnext.controllers.sales_and_purchase_return import make_return_doc

	lot = frappe.get_doc("Quality Control Lot", lot_name)
	lot.check_permission("read")

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
				"source_document_type": return_doc.doctype,
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
	saleable in the store — so this only proposes a default: the inspection's
	rejected unit count minus what prior returns already took, with the rejected
	serials still present in the warehouse. The row stays editable.
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

	if frappe.db.get_value("Quality Inspection", source_row.quality_inspection, "docstatus") != 1:
		return

	inspection = frappe.get_doc("Quality Inspection", source_row.quality_inspection)
	if not inspection.get("unit_readings") or not flt(inspection.rejected_unit_quantity):
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

	outstanding = min(flt(inspection.rejected_unit_quantity) - already_returned, abs(flt(row.qty)))
	if outstanding <= 0:
		return

	row.qty = -outstanding
	if row.meta.has_field("received_qty"):
		row.received_qty = -outstanding

	rejected_serials = [
		serial
		for serial in inspection.get_unit_serials("Rejected")
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
