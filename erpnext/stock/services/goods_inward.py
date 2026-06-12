# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# License: GNU General Public License v3. See license.txt

"""From custody to stock: receipts made against a Goods Inward Note.

The note records what physically arrived; the receipt is where ownership,
stock and accounting begin. A receipt built from a note is capped to the
note's outstanding quantity — and where a custody inspection has already
decided the goods, to the accepted part of it — and submission books the
received quantity back onto the note, oldest arrival row first.
"""

import frappe
from frappe import _
from frappe.utils import flt, get_link_to_form

from erpnext.stock.doctype.goods_inward_note.goods_inward_note import RECEIPT_DOCTYPES

ORDER_REFERENCE_FIELDS = {
	"Purchase Receipt": ("purchase_order", "purchase_order_item"),
	"Subcontracting Receipt": ("subcontracting_order", "subcontracting_order_item"),
}


@frappe.whitelist()
def make_receipt_from_goods_inward_note(goods_inward_note: str):
	"""A receipt pre-filled with the note's outstanding quantities.

	Built through the order's own mapper (rates, taxes and supplied items come
	from there), then trimmed to what the note still holds — minus anything a
	custody inspection rejected, which never becomes stock.
	"""
	note = frappe.get_doc("Goods Inward Note", goods_inward_note)
	note.check_permission("read")
	receipt_doctype = RECEIPT_DOCTYPES[note.order_type]
	frappe.has_permission(receipt_doctype, "create", throw=True)

	if note.docstatus != 1:
		frappe.throw(
			_("Submit {0} before receiving against it.").format(
				get_link_to_form("Goods Inward Note", note.name)
			)
		)

	receivable = _receivable_by_order_item(note)
	if not receivable:
		frappe.throw(
			_("{0} has nothing left to receive.").format(get_link_to_form("Goods Inward Note", note.name)),
			title=_("Nothing To Receive"),
		)

	receipt = _map_order_to_receipt(note)
	order_item_field = ORDER_REFERENCE_FIELDS[receipt_doctype][1]

	kept = []
	for row in receipt.items:
		outstanding = receivable.get(row.get(order_item_field))
		if not outstanding:
			continue
		row.qty = min(flt(row.qty) or outstanding, outstanding)
		if row.meta.has_field("received_qty"):
			row.received_qty = row.qty
		row.goods_inward_note = note.name
		kept.append(row)

	if not kept:
		frappe.throw(
			_("{0} has nothing left to receive.").format(get_link_to_form("Goods Inward Note", note.name)),
			title=_("Nothing To Receive"),
		)

	receipt.set("items", kept)
	for idx, row in enumerate(receipt.items, start=1):
		row.idx = idx
	return receipt


def _map_order_to_receipt(note):
	if note.order_type == "Purchase Order":
		from erpnext.buying.doctype.purchase_order.mapper import make_purchase_receipt

		return make_purchase_receipt(note.order)

	from erpnext.subcontracting.doctype.subcontracting_order.subcontracting_order import (
		make_subcontracting_receipt,
	)

	return make_subcontracting_receipt(note.order)


def _receivable_by_order_item(note):
	"""Outstanding per order row, less whatever a custody inspection rejected."""
	receivable = {}
	for row in note.items:
		outstanding = note.outstanding_qty(row) - _rejected_in_custody(row)
		if outstanding > 0:
			receivable[row.order_item] = receivable.get(row.order_item, 0) + outstanding
	return receivable


def _rejected_in_custody(row):
	"""Quantity a custody inspection rejected that has not been returned yet.

	Rejected goods go back with the truck (returned quantity); until someone
	records that, they must not slip into a receipt.
	"""
	if not row.quality_inspection:
		return 0.0
	if frappe.db.get_value("Quality Inspection", row.quality_inspection, "docstatus") != 1:
		return 0.0

	inspection = frappe.get_doc("Quality Inspection", row.quality_inspection)
	if inspection.get("unit_readings"):
		rejected = flt(inspection.rejected_unit_quantity)
	elif inspection.status == "Rejected":
		rejected = flt(row.qty)
	else:
		rejected = 0.0
	return max(rejected - flt(row.returned_qty), 0.0)


def update_goods_inward_note_on_receipt(doc, method=None):
	"""Book a receipt's quantities back onto the notes it draws from."""
	if doc.doctype not in ("Purchase Receipt", "Subcontracting Receipt"):
		return

	drawn = {}
	for row in doc.get("items") or []:
		if not row.get("goods_inward_note"):
			continue
		order_item_field = ORDER_REFERENCE_FIELDS[doc.doctype][1]
		key = (row.goods_inward_note, row.get(order_item_field))
		drawn[key] = drawn.get(key, 0) + flt(row.get("qty"))

	if method == "before_submit":
		for (note_name, order_item), qty in drawn.items():
			_validate_note_capacity(note_name, order_item, qty)
	else:
		direction = -1 if method == "on_cancel" else +1
		notes = set()
		for (note_name, order_item), qty in drawn.items():
			_allocate_to_note(note_name, order_item, qty, direction)
			notes.add(note_name)
		for note_name in notes:
			_refresh_note_status(note_name)


def _note_rows(note_name, order_item):
	return frappe.get_all(
		"Goods Inward Note Item",
		filters={"parent": note_name, "order_item": order_item},
		fields=["name", "qty", "received_qty", "returned_qty", "quality_inspection"],
		order_by="idx",
	)


def _validate_note_capacity(note_name, order_item, qty):
	rows = _note_rows(note_name, order_item)
	capacity = sum(
		max(flt(row.qty) - flt(row.received_qty) - flt(row.returned_qty) - _rejected_in_custody(row), 0)
		for row in rows
	)
	if qty > capacity:
		frappe.throw(
			_(
				"Only {0} unit(s) of this order row remain receivable on {1} — what arrived, less "
				"what was already received, returned or rejected in custody."
			).format(capacity, get_link_to_form("Goods Inward Note", note_name)),
			title=_("More Than In Custody"),
		)


def _allocate_to_note(note_name, order_item, qty, direction):
	remaining = qty
	for row in _note_rows(note_name, order_item):
		if remaining <= 0:
			break
		if direction > 0:
			capacity = flt(row.qty) - flt(row.received_qty) - flt(row.returned_qty)
		else:
			capacity = flt(row.received_qty)
		if capacity <= 0:
			continue
		allocated = min(capacity, remaining)
		frappe.db.set_value(
			"Goods Inward Note Item",
			row.name,
			"received_qty",
			flt(row.received_qty) + direction * allocated,
			update_modified=False,
		)
		remaining -= allocated


def _refresh_note_status(note_name):
	frappe.get_doc("Goods Inward Note", note_name).update_status()
