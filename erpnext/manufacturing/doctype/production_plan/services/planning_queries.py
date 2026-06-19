# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Small query helpers shared by Production Plan material planning."""

import json

import frappe
from frappe.query_builder.functions import IfNull, Sum
from pypika.terms import ExistsCriterion

from erpnext.manufacturing.doctype.work_order.work_order import get_item_details


def get_uom_conversion_factor(item_code, uom):
	return frappe.db.get_value(
		"UOM Conversion Detail", {"parent": item_code, "uom": uom}, "conversion_factor"
	)


@frappe.whitelist()
def get_bin_details(
	row: str | dict, company: str, for_warehouse: str | None = None, all_warehouse: bool = False
):
	frappe.has_permission("Production Plan", "read", throw=True)

	if isinstance(row, str):
		row = frappe._dict(json.loads(row))

	bin = frappe.qb.DocType("Bin")
	subquery = _bin_warehouse_subquery(bin, company, row, for_warehouse, all_warehouse)
	query = (
		frappe.qb.from_(bin)
		.select(bin.warehouse, *_bin_qty_columns(bin))
		.where((bin.item_code == row["item_code"]) & (bin.warehouse.isin(subquery)))
		.groupby(bin.item_code, bin.warehouse)
	)
	return query.run(as_dict=True)


def _bin_warehouse_subquery(bin, company, row, for_warehouse, all_warehouse):
	wh = frappe.qb.DocType("Warehouse")
	subquery = frappe.qb.from_(wh).select(wh.name).where(wh.company == company)

	warehouse = ""
	if not all_warehouse:
		warehouse = for_warehouse or row.get("source_warehouse") or row.get("default_warehouse")

	if warehouse:
		lft, rgt = frappe.db.get_value("Warehouse", warehouse, ["lft", "rgt"])
		subquery = subquery.where((wh.lft >= lft) & (wh.rgt <= rgt) & (wh.name == bin.warehouse))
	return subquery


def _bin_qty_columns(bin):
	return [
		IfNull(Sum(bin.projected_qty), 0).as_("projected_qty"),
		IfNull(Sum(bin.actual_qty), 0).as_("actual_qty"),
		IfNull(Sum(bin.ordered_qty), 0).as_("ordered_qty"),
		IfNull(Sum(bin.reserved_qty_for_production), 0).as_("reserved_qty_for_production"),
		IfNull(Sum(bin.planned_qty), 0).as_("planned_qty"),
	]


def get_warehouse_list(warehouses):
	warehouse_list = []

	if isinstance(warehouses, str):
		warehouses = json.loads(warehouses)

	for row in warehouses:
		child_warehouses = frappe.db.get_descendants("Warehouse", row.get("warehouse"))
		if child_warehouses:
			warehouse_list.extend(child_warehouses)
		else:
			warehouse_list.append(row.get("warehouse"))

	return warehouse_list


@frappe.whitelist()
def get_item_data(item_code: str):
	frappe.has_permission("Item", "read", throw=True)

	item_details = get_item_details(item_code)

	return {
		"bom_no": item_details.get("bom_no"),
		"stock_uom": item_details.get("stock_uom"),
		"description": item_details.get("description"),
	}


def set_default_warehouses(row, default_warehouses):
	for field in ["wip_warehouse", "fg_warehouse", "scrap_warehouse"]:
		if not row.get(field):
			row[field] = default_warehouses.get(field)


def get_sales_orders(self):
	bom = frappe.qb.DocType("BOM")
	so = frappe.qb.DocType("Sales Order")
	so_item = frappe.qb.DocType("Sales Order Item")

	bom_subquery = frappe.qb.from_(bom).select(bom.name).where(bom.is_active == 1)
	query = _open_so_base_query(self, so, so_item)
	query = _apply_open_so_filters(self, query, so, so_item)

	if self.item_code and frappe.db.exists("Item", self.item_code):
		query = query.where(so_item.item_code == self.item_code)
		bom_subquery = bom_subquery.where(self.get_bom_item_condition() or bom.item == so_item.item_code)

	packed_subquery = _packed_item_subquery(bom, so, so_item)
	query = query.where(ExistsCriterion(bom_subquery) | ExistsCriterion(packed_subquery))
	return query.run(as_dict=True)


def _open_so_base_query(plan, so, so_item):
	return (
		frappe.qb.from_(so)
		.from_(so_item)
		.select(so.name, so.transaction_date, so.customer, so.base_grand_total)
		.distinct()
		.where(
			(so_item.parent == so.name)
			& (so.docstatus == 1)
			& (so.status.notin(["Stopped", "Closed"]))
			& (so.company == plan.company)
			& (so_item.qty > so_item.production_plan_qty)
		)
	)


def _apply_open_so_filters(plan, query, so, so_item):
	date_field_mapper = {
		"from_date": so.transaction_date >= plan.from_date,
		"to_date": so.transaction_date <= plan.to_date,
		"from_delivery_date": so_item.delivery_date >= plan.from_delivery_date,
		"to_delivery_date": so_item.delivery_date <= plan.to_delivery_date,
	}
	for field, value in date_field_mapper.items():
		if plan.get(field):
			query = query.where(value)

	for field in ("customer", "project", "sales_order_status"):
		if plan.get(field):
			so_field = "status" if field == "sales_order_status" else field
			query = query.where(so[so_field] == plan.get(field))
	return query


def _packed_item_subquery(bom, so, so_item):
	pi = frappe.qb.DocType("Packed Item")
	bom_exists = ExistsCriterion(
		frappe.qb.from_(bom).select(bom.name).where((bom.item == pi.item_code) & (bom.is_active == 1))
	)
	return (
		frappe.qb.from_(pi)
		.select(pi.name)
		.where((pi.parent == so.name) & (pi.parent_item == so_item.item_code) & bom_exists)
	)
