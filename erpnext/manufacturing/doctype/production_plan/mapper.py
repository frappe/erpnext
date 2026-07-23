# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Query/data helpers for Production Plan (extracted from production_plan.py)."""


import frappe


@frappe.whitelist()
def get_so_details(sales_order: str):
	frappe.has_permission("Sales Order", "read", throw=True)

	return frappe.db.get_value(
		"Sales Order", sales_order, ["transaction_date", "customer", "grand_total"], as_dict=1
	)


@frappe.whitelist()
def sales_order_query(
	doctype: str | None = None,
	txt: str | None = None,
	searchfield: str | None = None,
	start: int | None = None,
	page_len: int | None = None,
	filters: dict | None = None,
):
	frappe.has_permission("Production Plan", throw=True)

	filters = filters or {}
	so_table = frappe.qb.DocType("Sales Order")
	table = frappe.qb.DocType("Sales Order Item")

	query = (
		frappe.qb.from_(so_table)
		.join(table)
		.on(table.parent == so_table.name)
		.select(table.parent)
		.distinct()
		.where((table.qty > table.production_plan_qty) & (table.docstatus == 1))
	)
	query = _apply_sales_order_filters(query, so_table, table, filters, txt)
	query = _paginate(query, start, page_len)
	return query.run()


def _paginate(query, start, page_len):
	if page_len:
		query = query.limit(page_len)
	if start:
		query = query.offset(start)
	return query


def _apply_sales_order_filters(query, so_table, table, filters, txt):
	if filters.get("company"):
		query = query.where(so_table.company == filters.get("company"))
	if filters.get("sales_orders"):
		query = query.where(so_table.name.isin(filters.get("sales_orders")))
	if filters.get("item_code"):
		query = query.where(table.item_code == filters.get("item_code"))
	if txt:
		query = query.where(table.parent.like(f"%{txt}%"))
	return query
