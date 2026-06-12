# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# License: GNU General Public License v3. See license.txt

"""From custody to stock: receipts made against a Goods Inward Note.

The note records what physically arrived; the receipt is where ownership,
stock and accounting begin. A receipt built from a note is capped to the
note's outstanding quantity — under a Block trigger, to the units the custody
verdicts have decided so far: tranches release as their inspections submit.
The verdicts prefill the accepted/rejected split: rejected units ride the
receipt as rejected quantity into a Rejected warehouse, the standard
purchase-return path from there. Submission books the full received quantity
(accepted and rejected) back onto the note, oldest arrival row first.
"""

import frappe
from frappe import _
from frappe.utils import flt, get_link_to_form

from erpnext.stock.doctype.goods_inward_note.goods_inward_note import (
	ORDER_REFERENCE_FIELDS,
	RECEIPT_DOCTYPES,
	get_custody_verdicts,
)


@frappe.whitelist()
def make_receipt_from_goods_inward_note(goods_inward_note: str):
	"""A receipt pre-filled with the note's outstanding quantities.

	Built through the order's own mapper (rates, taxes and supplied items come
	from there), then trimmed to what the note still holds and the custody
	verdicts have released, with the accepted/rejected split prefilled.
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

	verdicts = _verdicts_by_row(note)
	caps, warned = _custody_inspection_state(note, verdicts)
	receivable = _receivable_by_order_item(note, caps)
	if not receivable:
		if caps:
			frappe.throw(
				_(
					"The goods on {0} await a quality inspection in custody and cannot be "
					"received until it is submitted."
				).format(get_link_to_form("Goods Inward Note", note.name)),
				title=_("Awaiting Inspection"),
			)
		frappe.throw(
			_("{0} has nothing left to receive.").format(get_link_to_form("Goods Inward Note", note.name)),
			title=_("Nothing To Receive"),
		)
	if warned:
		frappe.msgprint(
			_("No custody inspection was recorded for: {0}.").format(
				", ".join(get_link_to_form("Item", item) for item in sorted(warned))
			),
			indicator="orange",
			alert=True,
		)

	receipt = _map_order_to_receipt(note)
	order_item_field = ORDER_REFERENCE_FIELDS[receipt_doctype][1]
	rejected_pool = _custody_rejected_by_order_item(note, verdicts)
	rejected_warehouse = _default_rejected_warehouse(note.company) if rejected_pool else None

	kept = []
	for row in receipt.items:
		order_item = row.get(order_item_field)
		outstanding = receivable.get(order_item)
		if not outstanding:
			continue
		total = min(flt(row.qty) or outstanding, outstanding)
		rejected = min(rejected_pool.get(order_item, 0), total)
		if rejected:
			rejected_pool[order_item] -= rejected
		row.qty = total - rejected
		row.rejected_qty = rejected
		if row.meta.has_field("received_qty"):
			row.received_qty = total
		if rejected and rejected_warehouse and not row.get("rejected_warehouse"):
			row.rejected_warehouse = rejected_warehouse
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


def _verdicts_by_row(note):
	"""The custody verdicts of every note row, fetched once for the caller."""
	return {row.name: get_custody_verdicts(row.name, row_qty=row.qty) for row in note.items}


def _custody_inspection_state(note, verdicts=None):
	"""What the note's quality triggers hold back or grumble about.

	Returns (receivable caps by row name, item codes to warn about). A Block
	trigger releases a row's quantity tranche by tranche: only units a custody
	verdict has decided may be received, the rest wait. Warn only flags the
	missing inspection. Fully decided rows carry no cap — what the verdicts
	rejected is handled separately.
	"""
	from erpnext.stock.services.quality_trigger_resolution import resolve_inspection_points

	if verdicts is None:
		verdicts = _verdicts_by_row(note)

	caps, warned = {}, set()
	for point in resolve_inspection_points(note):
		row = point.row
		verdict = verdicts[row.name]
		# every arrived unit wants a verdict before it becomes stock
		if flt(verdict.decided - flt(row.qty), 6) >= 0:
			continue
		if point.quality_control_mode == "Block":
			# decided units may go, less what earlier receipts took
			caps[row.name] = max(verdict.decided - flt(row.received_qty), 0)
		elif point.quality_control_mode == "Warn":
			warned.add(row.get("item_code"))
	return caps, warned


def _receivable_by_order_item(note, caps=None):
	"""Outstanding per order row, within what a Block trigger has released."""
	receivable = {}
	for row in note.items:
		outstanding = note.outstanding_qty(row)
		cap = (caps or {}).get(row.name)
		if cap is not None:
			outstanding = min(outstanding, cap)
		if outstanding > 0:
			receivable[row.order_item] = receivable.get(row.order_item, 0) + outstanding
	return receivable


def _custody_rejected_by_order_item(note, verdicts):
	"""Units the custody verdicts rejected that still await a receipt.

	They prefill the receipt's rejected quantity — rejected goods enter stock
	in a Rejected warehouse, where the standard purchase-return path takes
	over. Whatever a prior receipt already booked as rejected is not proposed
	again.
	"""
	rejected = {}
	for row in note.items:
		amount = verdicts[row.name].rejected
		if amount > 0:
			rejected[row.order_item] = rejected.get(row.order_item, 0) + amount

	if rejected:
		receipt_doctype = RECEIPT_DOCTYPES[note.order_type]
		order_item_field = ORDER_REFERENCE_FIELDS[receipt_doctype][1]
		for prior in frappe.get_all(
			receipt_doctype + " Item",
			filters={"goods_inward_note": note.name, "docstatus": 1},
			fields=[f"{order_item_field} as order_item", "rejected_qty"],
		):
			if prior.order_item in rejected:
				rejected[prior.order_item] = max(rejected[prior.order_item] - flt(prior.rejected_qty), 0)

	return {order_item: amount for order_item, amount in rejected.items() if amount > 0}


def _default_rejected_warehouse(company):
	"""The company's Rejected warehouse, when there is exactly one to propose."""
	rejected_warehouses = frappe.get_all(
		"Warehouse",
		filters={"warehouse_type": "Rejected", "company": company, "is_group": 0, "disabled": 0},
		pluck="name",
	)
	return rejected_warehouses[0] if len(rejected_warehouses) == 1 else None


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
		# rejected units leave custody too — into the Rejected warehouse
		taken = flt(row.get("received_qty")) or (flt(row.get("qty")) + flt(row.get("rejected_qty")))
		drawn[key] = drawn.get(key, 0) + taken

	caps_by_note = {}

	def caps_on(note_name):
		if note_name not in caps_by_note:
			note = frappe.get_doc("Goods Inward Note", note_name)
			caps_by_note[note_name] = _custody_inspection_state(note)[0]
		return caps_by_note[note_name]

	if method == "before_submit":
		for (note_name, order_item), qty in drawn.items():
			_validate_note_capacity(note_name, order_item, qty, caps_on(note_name))
	else:
		direction = -1 if method == "on_cancel" else +1
		notes = set()
		for (note_name, order_item), qty in drawn.items():
			# allocation honours what the verdicts released; cancellation unwinds anywhere
			caps = caps_on(note_name) if direction > 0 else None
			_allocate_to_note(note_name, order_item, qty, direction, caps)
			notes.add(note_name)
		for note_name in notes:
			_refresh_note_status(note_name)


def _note_rows(note_name, order_item):
	"""The note's rows for an order row, locked until the booking commits.

	Capacity is validated and allocated in separate steps; the row lock keeps
	a concurrent receipt from drawing the same custody units in between.
	"""
	table = frappe.qb.DocType("Goods Inward Note Item")
	return (
		frappe.qb.from_(table)
		.select(table.name, table.qty, table.received_qty)
		.where((table.parent == note_name) & (table.order_item == order_item))
		.orderby(table.idx)
		.for_update()
	).run(as_dict=True)


def _validate_note_capacity(note_name, order_item, qty, caps=None):
	capacity = 0.0
	for row in _note_rows(note_name, order_item):
		room = max(flt(row.qty) - flt(row.received_qty), 0)
		cap = (caps or {}).get(row.name)
		if cap is not None:
			room = min(room, cap)
		capacity += room
	if qty > capacity:
		frappe.throw(
			_(
				"Only {0} unit(s) of this order row remain receivable on {1} — what arrived, less "
				"what was already received or still awaiting inspection in custody."
			).format(capacity, get_link_to_form("Goods Inward Note", note_name)),
			title=_("More Than In Custody"),
		)


def _allocate_to_note(note_name, order_item, qty, direction, caps=None):
	remaining = qty
	for row in _note_rows(note_name, order_item):
		if remaining <= 0:
			break
		if direction > 0:
			capacity = flt(row.qty) - flt(row.received_qty)
			cap = (caps or {}).get(row.name)
			if cap is not None:
				capacity = min(capacity, cap)
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
