from collections import defaultdict

import frappe

from erpnext.stock.doctype.stock_entry.services.subcontracting import get_supplied_items
from erpnext.stock.utils import get_bin


def execute():
	"""Link earlier alternative item transfers and their returns to their Subcontracting Order row, so reserved qty counts them."""
	rows = get_unlinked_rows()
	originals = defaultdict(set)
	for row in rows:
		if not row.is_return:
			originals[(row.subcontracting_order, row.item_code, row.subcontracted_item)].add(
				row.original_item
			)

	orders = set()
	for row in rows:
		candidates = originals.get((row.subcontracting_order, row.item_code, row.subcontracted_item), set())
		original_item = row.original_item or (next(iter(candidates)) if len(candidates) == 1 else None)
		if rm_detail := get_order_row(row, original_item):
			frappe.db.set_value(
				"Stock Entry Detail",
				row.name,
				{"sco_rm_detail": rm_detail, "original_item": original_item},
				update_modified=False,
			)
			orders.add(row.subcontracting_order)

	for order in orders:
		refresh_supplied_and_reserved_qty(order)


def get_unlinked_rows():
	"""Alternative item sends, and returns, of open Subcontracting Orders without an order row."""
	entry = frappe.qb.DocType("Stock Entry")
	row = frappe.qb.DocType("Stock Entry Detail")
	order = frappe.qb.DocType("Subcontracting Order")
	return (
		frappe.qb.from_(row)
		.inner_join(entry)
		.on(entry.name == row.parent)
		.inner_join(order)
		.on(order.name == entry.subcontracting_order)
		.select(
			row.name,
			row.item_code,
			row.original_item,
			row.subcontracted_item,
			row.s_warehouse,
			row.t_warehouse,
			entry.is_return,
			entry.subcontracting_order,
		)
		.where(
			(entry.docstatus == 1)
			& (
				(
					(entry.purpose == "Send to Subcontractor")
					& (row.original_item.isnotnull())
					& (row.original_item != "")
				)
				| (entry.is_return == 1)
			)
			& (row.sco_rm_detail.isnull() | (row.sco_rm_detail == ""))
			& (order.docstatus == 1)
			& (order.status != "Closed")
			& (order.per_received < 100)
		)
		.orderby(entry.posting_date, entry.posting_time, entry.creation)
	).run(as_dict=True)


def get_order_row(row, original_item):
	"""The one order row of the original item in the reserve warehouse; none when it is missing or ambiguous."""
	if not original_item:
		return None

	matches = frappe.get_all(
		"Subcontracting Order Supplied Item",
		filters={
			"parent": row.subcontracting_order,
			"rm_item_code": original_item,
			"main_item_code": row.subcontracted_item,
			"reserve_warehouse": row.t_warehouse if row.is_return else row.s_warehouse,
		},
		pluck="name",
	)
	return matches[0] if len(matches) == 1 else None


def refresh_supplied_and_reserved_qty(order):
	supplied_items = get_supplied_items(order)
	for row in frappe.get_all(
		"Subcontracting Order Supplied Item",
		filters={"parent": order},
		fields=["name", "rm_item_code", "reserve_warehouse"],
	):
		frappe.db.set_value(
			"Subcontracting Order Supplied Item",
			row.name,
			supplied_items.get(row.name) or {"supplied_qty": 0, "returned_qty": 0, "total_supplied_qty": 0},
			update_modified=False,
		)
		if row.reserve_warehouse:
			get_bin(row.rm_item_code, row.reserve_warehouse).update_reserved_qty_for_sub_contracting()
