# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.query_builder.functions import Sum
from frappe.utils import flt


def execute(filters=None):
	validate_warehouse(filters)
	columns = get_columns()
	data = get_data(filters.warehouse, filters.show_disabled_items)
	return columns, data


def validate_warehouse(filters):
	company = filters.company
	warehouse = filters.warehouse
	if not frappe.db.exists("Warehouse", {"name": warehouse, "company": company}):
		frappe.throw(_("Warehouse: {0} does not belong to {1}").format(warehouse, company))


def get_columns():
	columns = [
		{
			"label": _("Item Code"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 200,
		},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 200},
		{"label": _("Serial No Count"), "fieldname": "total", "fieldtype": "Float", "width": 150},
		{"label": _("Stock Qty"), "fieldname": "stock_qty", "fieldtype": "Float", "width": 150},
		{"label": _("Difference"), "fieldname": "difference", "fieldtype": "Float", "width": 150},
	]

	return columns


def get_warehouses(warehouse):
	if frappe.db.get_value("Warehouse", warehouse, "is_group"):
		from erpnext.stock.doctype.warehouse.warehouse import get_child_warehouses

		return get_child_warehouses(warehouse)

	return [warehouse]


def get_data(warehouse, show_disabled_items):
	# A group (parent) warehouse holds no stock itself; stock lives in its child
	# warehouses. Expand it to all its descendants so the report aggregates them.
	warehouses = get_warehouses(warehouse)

	filters = {"has_serial_no": True}
	if not show_disabled_items:
		filters["disabled"] = False
	serial_item_list = frappe.get_all(
		"Item",
		filters=filters,
		fields=["item_code", "item_name"],
	)

	status_list = ["Active", "Expired"]
	data = []
	for item in serial_item_list:
		total_serial_no = frappe.db.count(
			"Serial No",
			filters={
				"item_code": item.item_code,
				"status": ("in", status_list),
				"warehouse": ("in", warehouses),
			},
		)

		bin_table = frappe.qb.DocType("Bin")
		bin_qty = (
			frappe.qb.from_(bin_table)
			.select(Sum(bin_table.actual_qty))
			.where(bin_table.item_code == item.item_code)
			.where(bin_table.warehouse.isin(warehouses))
		).run()

		# Sum is null when no Bin record exists for the item in these warehouses.
		actual_qty = flt(bin_qty[0][0]) if bin_qty else 0

		difference = total_serial_no - actual_qty

		row = {
			"item_code": item.item_code,
			"item_name": item.item_name,
			"total": total_serial_no,
			"stock_qty": actual_qty,
			"difference": difference,
		}

		data.append(row)

	return data
