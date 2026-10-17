from collections import defaultdict

import frappe

from erpnext.stock.doctype.stock_entry.stock_entry import get_supplied_items
from erpnext.stock.utils import get_bin

ORDER_FLOWS = (
	("Subcontracting Order", "subcontracting_order", "sco_rm_detail", "Subcontracting Order Supplied Item"),
	("Purchase Order", "purchase_order", "po_detail", "Purchase Order Item Supplied"),
)


def execute():
	"""Link earlier alternative item transfers and their returns to their order row, so reserved qty counts them."""
	for order_doctype, order_field, rm_detail_field, supplied_items_doctype in ORDER_FLOWS:
		rows = get_unlinked_rows(order_doctype, order_field, rm_detail_field)
		originals = defaultdict(set)
		for row in rows:
			if not row.is_return:
				originals[(row.order, row.item_code, row.subcontracted_item)].add(row.original_item)

		orders = set()
		for row in rows:
			candidates = originals.get((row.order, row.item_code, row.subcontracted_item), set())
			original_item = row.original_item or (next(iter(candidates)) if len(candidates) == 1 else None)
			if rm_detail := get_order_row(row, original_item, supplied_items_doctype):
				frappe.db.set_value(
					"Stock Entry Detail",
					row.name,
					{rm_detail_field: rm_detail, "original_item": original_item},
					update_modified=False,
				)
				orders.add(row.order)

		for order in orders:
			refresh_supplied_and_reserved_qty(
				order, order_doctype, order_field, rm_detail_field, supplied_items_doctype
			)


def get_unlinked_rows(order_doctype, order_field, rm_detail_field):
	"""Alternative item sends, and returns, of open orders without an order row."""
	entry = frappe.qb.DocType("Stock Entry")
	row = frappe.qb.DocType("Stock Entry Detail")
	order = frappe.qb.DocType(order_doctype)
	query = (
		frappe.qb.from_(row)
		.inner_join(entry)
		.on(entry.name == row.parent)
		.inner_join(order)
		.on(order.name == entry[order_field])
		.select(
			row.name,
			row.item_code,
			row.original_item,
			row.subcontracted_item,
			row.s_warehouse,
			row.t_warehouse,
			entry.is_return,
			entry[order_field].as_("order"),
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
			& (row[rm_detail_field].isnull() | (row[rm_detail_field] == ""))
			& (order.docstatus == 1)
			& (order.status != "Closed")
			& (order.per_received < 100)
		)
		.orderby(entry.posting_date, entry.posting_time, entry.creation)
	)
	if order_doctype == "Purchase Order":
		query = query.where(order.is_old_subcontracting_flow == 1)
	return query.run(as_dict=True)


def get_order_row(row, original_item, supplied_items_doctype):
	"""The one order row of the original item in the reserve warehouse; none when it is missing or ambiguous."""
	if not original_item:
		return None

	matches = frappe.get_all(
		supplied_items_doctype,
		filters={
			"parent": row.order,
			"rm_item_code": original_item,
			"main_item_code": row.subcontracted_item,
			"reserve_warehouse": row.t_warehouse if row.is_return else row.s_warehouse,
		},
		pluck="name",
	)
	return matches[0] if len(matches) == 1 else None


def refresh_supplied_and_reserved_qty(
	order, order_doctype, order_field, rm_detail_field, supplied_items_doctype
):
	supplied_items = get_supplied_items(order, rm_detail_field, order_field)
	for row in frappe.get_all(
		supplied_items_doctype,
		filters={"parent": order},
		fields=["name", "rm_item_code", "reserve_warehouse"],
	):
		frappe.db.set_value(
			supplied_items_doctype,
			row.name,
			supplied_items.get(row.name) or {"supplied_qty": 0, "returned_qty": 0, "total_supplied_qty": 0},
			update_modified=False,
		)
		if row.reserve_warehouse:
			get_bin(row.rm_item_code, row.reserve_warehouse).update_reserved_qty_for_sub_contracting(
				subcontract_doctype=order_doctype
			)
