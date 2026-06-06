# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Stock reservation for Production Plan (extracted from production_plan.py)."""


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder import Case
from frappe.query_builder.functions import IfNull, Sum
from frappe.utils import flt, parse_json

from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import StockReservation

_RESERVATION_TABLES = {
	"sub_assembly_items": {
		"table_name": "sub_assembly_items",
		"qty_field": "required_qty",
		"warehouse_field": "fg_warehouse",
	},
	"mr_items": {
		"table_name": "mr_items",
		"qty_field": "required_bom_qty",
		"warehouse_field": "warehouse",
	},
}


def get_reserved_qty_for_production_plan(item_code, warehouse):
	from erpnext.manufacturing.doctype.work_order.work_order import get_reserved_qty_for_production

	non_completed_production_plans = get_non_completed_production_plans()
	reserved = _production_plan_reserved_qty(item_code, warehouse, non_completed_production_plans)
	if reserved is None:
		return None

	for_production = flt(
		get_reserved_qty_for_production(
			item_code, warehouse, non_completed_production_plans, check_production_plan=True
		)
	)
	if for_production > reserved:
		return 0.0
	return reserved - for_production


def _production_plan_reserved_qty(item_code, warehouse, non_completed_production_plans):
	table = frappe.qb.DocType("Production Plan")
	child = frappe.qb.DocType("Material Request Plan Item")
	qty = (
		Case().when(child.quantity == 0, child.required_bom_qty).else_(child.quantity)
		* child.conversion_factor
	)
	query = (
		frappe.qb.from_(table)
		.inner_join(child)
		.on(table.name == child.parent)
		.select(Sum(qty))
		.where(_plan_reserved_filter(table, child, item_code, warehouse))
	)
	if non_completed_production_plans:
		query = query.where(table.name.isin(non_completed_production_plans))

	result = query.run()
	return flt(result[0][0]) if result and result[0][0] is not None else None


def _plan_reserved_filter(table, child, item_code, warehouse):
	return (
		(table.docstatus == 1)
		& (child.item_code == item_code)
		& (child.warehouse == warehouse)
		& (table.status.notin(["Completed", "Closed"]))
	)


def get_non_completed_production_plans():
	table = frappe.qb.DocType("Production Plan")

	return (
		frappe.qb.from_(table)
		.select(table.name)
		.distinct()
		.where((table.docstatus == 1) & (table.status.notin(["Completed", "Closed"])))
	).run(pluck="name")


def get_reserved_qty_for_sub_assembly(item_code, warehouse):
	table = frappe.qb.DocType("Production Plan")
	child = frappe.qb.DocType("Production Plan Sub Assembly Item")
	qty_field = Case().when(child.qty > 0, child.qty).else_(child.required_qty) - IfNull(
		child.wo_produced_qty, 0
	)
	result = (
		frappe.qb.from_(table)
		.inner_join(child)
		.on(table.name == child.parent)
		.select(Sum(qty_field))
		.where(_sub_assembly_reserved_filter(table, child, item_code, warehouse))
	).run()

	if not result or result[0][0] is None:
		return None

	qty = flt(result[0][0])
	return qty if qty > 0 else 0.0


def _sub_assembly_reserved_filter(table, child, item_code, warehouse):
	return (
		(table.docstatus == 1)
		& (child.production_item == item_code)
		& (child.fg_warehouse == warehouse)
		& (table.status.notin(["Completed", "Closed"]))
	)


@frappe.whitelist()
def make_stock_reservation_entries(
	doc: str | Document, items: str | list | None = None, table_name: str | None = None, notify: bool = False
):
	"""Whitelisted entry point: verify Production Plan write access, then reserve stock."""
	if isinstance(doc, str):
		doc = parse_json(doc)
		doc = frappe.get_doc("Production Plan", doc.get("name"))

	frappe.has_permission("Production Plan", "write", doc=doc, throw=True)
	reserve_stock_for_production_plan(doc, items=items, table_name=table_name, notify=notify)


def reserve_stock_for_production_plan(
	doc: Document, items: str | list | None = None, table_name: str | None = None, notify: bool = False
):
	"""Reserve stock for a Production Plan. Internal: no permission check (also called
	from the Production Plan submit/cancel lifecycle)."""
	if items and isinstance(items, str):
		items = parse_json(items)

	for child_table_name, kwargs in _RESERVATION_TABLES.items():
		if table_name and table_name != child_table_name:
			continue
		_reserve_or_cancel_plan_table(doc, items, kwargs)

	doc.reload()


def _reserve_or_cancel_plan_table(doc, items, kwargs):
	sre = StockReservation(doc, items=items, kwargs=kwargs)
	if doc.docstatus == 1:
		if sre.make_stock_reservation_entries():
			frappe.msgprint(_("Stock Reservation Entries Created"), alert=True)
	elif doc.docstatus == 2:
		sre.cancel_stock_reservation_entries()


@frappe.whitelist()
def cancel_stock_reservation_entries(doc: str | Document, sre_list: str | list):
	"""Whitelisted entry point: verify Production Plan write access, then cancel reservations."""
	if isinstance(doc, str):
		doc = parse_json(doc)
		doc = frappe.get_doc("Production Plan", doc.get("name"))

	frappe.has_permission("Production Plan", "write", doc=doc, throw=True)
	sre = StockReservation(doc)
	sre.cancel_stock_reservation_entries(sre_list)

	doc.reload()
