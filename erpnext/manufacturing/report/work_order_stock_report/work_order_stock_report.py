# Copyright (c) 2017, Velometro Mobility Inc and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.query_builder.functions import IfNull, Sum
from frappe.utils import flt

from erpnext.stock.doctype.company_restriction.company_restriction import get_allowed_companies_condition
from erpnext.stock.doctype.warehouse.warehouse import get_child_warehouses


def execute(filters=None):
	wo_list = get_work_orders()
	data = get_item_list(wo_list, filters)
	columns = get_columns()
	return columns, data


def get_item_list(wo_list, filters):
	if not wo_list:
		return []

	descriptions = get_bom_descriptions(wo_list)
	items_by_order = get_work_order_items(wo_list)
	stock = get_stock(items_by_order, filters)
	set_aside_transferred_stock(wo_list, stock)
	warehouses = set(get_child_warehouses(filters.warehouse)) if filters.get("warehouse") else None

	out = []
	for wo_details in wo_list:
		for item in items_by_order.get(wo_details.name, []):
			if warehouses and item.source_warehouse and item.source_warehouse not in warehouses:
				continue
			out.append(get_row(wo_details, item, descriptions, stock, filters))

	return sorted(out, key=lambda row: row.work_order)


def get_row(wo_details, item, descriptions, stock, filters):
	warehouse = item.source_warehouse or filters.get("warehouse")
	pending_qty = flt(wo_details.qty) - flt(wo_details.produced_qty)
	qty_per_unit = flt(item.required_qty) / flt(wo_details.qty) if flt(wo_details.qty) else 0.0
	in_wip_qty = get_in_wip_qty(item)
	needed_qty = max(qty_per_unit * pending_qty - in_wip_qty, 0.0)
	available_qty = allocate_stock(stock, (item.item_code, warehouse), needed_qty) + in_wip_qty
	build_qty = available_qty / qty_per_unit if qty_per_unit else flt(wo_details.qty)
	in_stock = 1 if build_qty >= pending_qty else 0

	return frappe._dict(
		{
			"work_order": wo_details.name,
			"status": wo_details.status,
			"req_items": 1,
			"instock": in_stock,
			"description": descriptions.get(wo_details.bom_no),
			"source_warehouse": item.source_warehouse,
			"item_code": item.item_code,
			"bom_no": wo_details.bom_no,
			"qty": wo_details.qty,
			"buildable_qty": wo_details.qty if in_stock else build_qty,
			"ready_to_build": "Y" if in_stock else "N",
		}
	)


def get_in_wip_qty(item):
	return max(flt(item.transferred_qty) - flt(item.consumed_qty), 0.0)


def set_aside_transferred_stock(wo_list, stock):
	for (item_code, warehouse), qty in get_stock_held_in_wip(wo_list).items():
		if (item_code, warehouse) in stock:
			stock[(item_code, warehouse)] = max(stock[(item_code, warehouse)] - qty, 0.0)


WIP_STOCK_MOVES = (
	("Material Transfer for Manufacture", 0, "t_warehouse", 1),
	("Material Transfer for Manufacture", 1, "s_warehouse", -1),
	("Manufacture", None, "s_warehouse", -1),
	("Material Consumption for Manufacture", None, "s_warehouse", -1),
)


def get_stock_held_in_wip(wo_list):
	held_by_order = {}
	for purpose, is_return, warehouse_field, sign in WIP_STOCK_MOVES:
		for row in get_work_order_stock_moves(wo_list, purpose, is_return, warehouse_field):
			key = (row.work_order, row.item_code, row.warehouse)
			held_by_order[key] = held_by_order.get(key, 0.0) + sign * flt(row.qty)

	held = {}
	for (_work_order, item_code, warehouse), qty in held_by_order.items():
		if qty > 0:
			held[(item_code, warehouse)] = held.get((item_code, warehouse), 0.0) + qty

	return held


def get_work_order_stock_moves(wo_list, purpose, is_return, warehouse_field):
	se = frappe.qb.DocType("Stock Entry")
	sed = frappe.qb.DocType("Stock Entry Detail")
	warehouse = sed[warehouse_field]
	query = (
		frappe.qb.from_(sed)
		.inner_join(se)
		.on(se.name == sed.parent)
		.select(se.work_order, sed.item_code, warehouse.as_("warehouse"), Sum(sed.transfer_qty).as_("qty"))
		.where(
			(se.docstatus == 1)
			& (se.purpose == purpose)
			& (se.work_order.isin([d.name for d in wo_list]))
			& (IfNull(warehouse, "") != "")
		)
		.groupby(se.work_order, sed.item_code, warehouse)
	)
	if is_return is not None:
		query = query.where(IfNull(se.is_return, 0) == is_return)

	return query.run(as_dict=True)


def allocate_stock(stock, key, needed_qty):
	available_qty = flt(stock.get(key))
	stock[key] = available_qty - min(available_qty, needed_qty)
	return available_qty


def get_bom_descriptions(wo_list):
	boms = list({d.bom_no for d in wo_list if d.bom_no})
	return dict(
		frappe.get_all("BOM", filters={"name": ["in", boms]}, fields=["name", "description"], as_list=True)
	)


def get_work_order_items(wo_list):
	items_by_order = {}
	for row in frappe.get_all(
		"Work Order Item",
		filters={"parent": ["in", [d.name for d in wo_list]], "parenttype": "Work Order"},
		fields=["parent", "item_code", "source_warehouse", "required_qty", "transferred_qty", "consumed_qty"],
		order_by="idx",
	):
		items_by_order.setdefault(row.parent, []).append(row)

	return items_by_order


def get_stock(items_by_order, filters):
	rows = [row for items in items_by_order.values() for row in items]
	warehouses = {row.source_warehouse or filters.get("warehouse") for row in rows} - {None, ""}
	if not rows or not warehouses:
		return {}

	stock = {}
	for d in frappe.get_all(
		"Bin",
		filters={
			"item_code": ["in", list({row.item_code for row in rows})],
			"warehouse": ["in", list(warehouses)],
		},
		fields=["item_code", "warehouse", "actual_qty"],
	):
		stock[(d.item_code, d.warehouse)] = flt(d.actual_qty)

	return stock


def get_work_orders():
	work_order_filters = [
		{
			"docstatus": 1,
			"status": ("in", ["Not Started", "In Process", "Stock Reserved", "Stock Partially Reserved"]),
		}
	]
	if condition := get_allowed_companies_condition(frappe.qb.DocType("Work Order").company, "Work Order"):
		work_order_filters.append(condition)

	out = frappe.get_all(
		"Work Order",
		filters=work_order_filters,
		fields=["name", "status", "bom_no", "qty", "produced_qty", "planned_start_date"],
		order_by="planned_start_date asc, name asc",
	)

	return out


def get_columns():
	columns = [
		{
			"fieldname": "work_order",
			"label": _("Work Order"),
			"fieldtype": "Link",
			"options": "Work Order",
			"width": 110,
		},
		{"fieldname": "bom_no", "label": _("BOM"), "fieldtype": "Link", "options": "BOM", "width": 120},
		{
			"fieldname": "description",
			"label": _("Description"),
			"fieldtype": "Data",
			"options": "",
			"width": 230,
		},
		{
			"fieldname": "item_code",
			"label": _("Item Code"),
			"fieldtype": "Link",
			"options": "Item",
			"width": 110,
		},
		{
			"fieldname": "source_warehouse",
			"label": _("Source Warehouse"),
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 110,
		},
		{
			"fieldname": "qty",
			"label": _("Qty to Build"),
			"fieldtype": "Data",
			"options": "",
			"width": 110,
		},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "options": "", "width": 100},
		{
			"fieldname": "req_items",
			"label": _("# Req'd Items"),
			"fieldtype": "Data",
			"options": "",
			"width": 105,
		},
		{
			"fieldname": "instock",
			"label": _("# In Stock"),
			"fieldtype": "Data",
			"options": "",
			"width": 105,
		},
		{
			"fieldname": "buildable_qty",
			"label": _("Buildable Qty"),
			"fieldtype": "Data",
			"options": "",
			"width": 100,
		},
		{
			"fieldname": "ready_to_build",
			"label": _("Build All?"),
			"fieldtype": "Data",
			"options": "",
			"width": 90,
		},
	]

	return columns
