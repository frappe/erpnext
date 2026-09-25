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
	non_completed_production_plans = get_non_completed_production_plans()
	if not non_completed_production_plans:
		return None

	plan_reservations = _get_plan_reservations(item_code, non_completed_production_plans)
	if not plan_reservations:
		return None

	work_order_reservations = _get_work_order_reservations(item_code, non_completed_production_plans)
	reserved_qty = 0.0
	for plan, warehouses in plan_reservations.items():
		reserved_qty += _get_remaining_reserved_qty(
			warehouses, work_order_reservations.get(plan, 0.0), warehouse
		)

	return reserved_qty


def _get_remaining_reserved_qty(warehouse_reservations, work_order_qty, warehouse):
	total_reserved = sum(warehouse_reservations.values())
	if not total_reserved:
		return 0.0

	work_order_qty = min(flt(work_order_qty), total_reserved)
	warehouse_reserved = warehouse_reservations.get(warehouse, 0.0)
	return warehouse_reserved * (1 - work_order_qty / total_reserved)


def _get_plan_reservations(item_code, non_completed_production_plans):
	table = frappe.qb.DocType("Production Plan")
	child = frappe.qb.DocType("Material Request Plan Item")
	query = (
		frappe.qb.from_(table)
		.inner_join(child)
		.on(table.name == child.parent)
		.select(table.name, child.warehouse, Sum(child.required_bom_qty).as_("reserved_qty"))
		.where(
			(table.docstatus == 1)
			& (child.item_code == item_code)
			& (table.status.notin(["Completed", "Closed"]))
			& table.name.isin(non_completed_production_plans)
		)
		.groupby(table.name, child.warehouse)
	)

	reservations = {}
	for row in query.run(as_dict=True):
		reservations.setdefault(row.name, {})[row.warehouse] = flt(row.reserved_qty)
	return reservations


def _get_work_order_reservations(item_code, non_completed_production_plans):
	work_order = frappe.qb.DocType("Work Order")
	work_order_item = frappe.qb.DocType("Work Order Item")
	return {
		row.production_plan: flt(row.reserved_qty)
		for row in (
			frappe.qb.from_(work_order)
			.from_(work_order_item)
			.select(work_order.production_plan, Sum(work_order_item.required_qty).as_("reserved_qty"))
			.where(
				(work_order_item.item_code == item_code)
				& (work_order_item.parent == work_order.name)
				& (work_order.docstatus == 1)
				& work_order.production_plan.isin(non_completed_production_plans)
			)
			.groupby(work_order.production_plan)
		).run(as_dict=True)
	}


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


class ProductionPlanStockReservation:
	"""Reservation lifecycle for a Production Plan.

	A Production Plan reserves stock for two of its child tables: the sub-assembly
	items it will manufacture and the raw materials of its material-request rows
	(see ``_RESERVATION_TABLES``). On submit the rows are reserved; on cancel the
	reservations are released.

	The reserved-qty *query* helpers in this module
	(``get_reserved_qty_for_production_plan`` etc.) are read-only and answer "how
	much is reserved?" for bins and reports, so they stay module-level functions
	rather than methods, mirroring the engine's own query helpers.
	"""

	def __init__(self, doc):
		self.doc = doc

	def reserve(self, items: str | list | None = None, table_name: str | None = None, notify: bool = False):
		"""Reserve (docstatus 1) or release (docstatus 2) stock for the plan's tables."""
		if items and isinstance(items, str):
			items = parse_json(items)

		for child_table_name, kwargs in _RESERVATION_TABLES.items():
			if table_name and table_name != child_table_name:
				continue
			self._reserve_or_cancel_plan_table(items, kwargs)

		self.doc.reload()

	def _reserve_or_cancel_plan_table(self, items, kwargs):
		sre = StockReservation(self.doc, items=items, kwargs=kwargs)
		if self.doc.docstatus == 1:
			if sre.make_stock_reservation_entries():
				frappe.msgprint(_("Stock Reservation Entries Created"), alert=True)
		elif self.doc.docstatus == 2:
			sre.cancel_stock_reservation_entries()

	def cancel(self, sre_list: str | list | None = None):
		"""Cancel specific (or all) Stock Reservation Entries held by the plan."""
		StockReservation(self.doc).cancel_stock_reservation_entries(sre_list)
		self.doc.reload()


@frappe.whitelist()
def make_stock_reservation_entries(
	doc: str | Document, items: str | list | None = None, table_name: str | None = None, notify: bool = False
):
	"""Whitelisted entry point: verify Production Plan write access, then reserve stock."""
	doc = _load_production_plan(doc)
	frappe.has_permission("Production Plan", "write", doc=doc, throw=True)
	ProductionPlanStockReservation(doc).reserve(items=items, table_name=table_name, notify=notify)


def reserve_stock_for_production_plan(
	doc: Document, items: str | list | None = None, table_name: str | None = None, notify: bool = False
):
	"""Reserve stock for a Production Plan. Internal: no permission check (also called
	from the Production Plan submit/cancel lifecycle)."""
	ProductionPlanStockReservation(doc).reserve(items=items, table_name=table_name, notify=notify)


@frappe.whitelist()
def cancel_stock_reservation_entries(doc: str | Document, sre_list: str | list):
	"""Whitelisted entry point: verify Production Plan write access, then cancel reservations."""
	doc = _load_production_plan(doc)
	frappe.has_permission("Production Plan", "write", doc=doc, throw=True)
	ProductionPlanStockReservation(doc).cancel(sre_list)


def _load_production_plan(doc: str | dict | Document) -> Document:
	if isinstance(doc, str | dict):
		doc = parse_json(doc)
		doc = frappe.get_doc("Production Plan", doc.get("name"))
	return doc
