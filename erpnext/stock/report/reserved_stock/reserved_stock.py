# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import add_days, getdate


def execute(filters=None):
	columns, data = [], []

	validate_filters(filters)

	columns = get_columns()
	data = get_data(filters)

	return columns, data


def validate_filters(filters):
	if not filters:
		frappe.throw(_("Please set filters"))

	for field in ["company", "from_date", "to_date"]:
		if not filters.get(field):
			frappe.throw(_("Please set {0}").format(field))

	if filters.get("from_date") > filters.get("to_date"):
		frappe.throw(_("From Date cannot be greater than To Date"))


def get_data(filters):
	query_filters = [
		["docstatus", "=", 1],
		["company", "=", filters.get("company")],
		["creation", ">=", getdate(filters.get("from_date"))],
		["creation", "<", add_days(filters.get("to_date"), 1)],
	]
	for field in [
		"item_code",
		"warehouse",
		"voucher_type",
		"voucher_no",
		"from_voucher_type",
		"from_voucher_no",
		"reservation_based_on",
		"status",
		"project",
	]:
		if value := filters.get(field):
			query_filters.append([field, "=", value])

	if value := filters.get("stock_reservation_entry"):
		query_filters.append(["name", "=", value])

	data = frappe.get_list(
		"Stock Reservation Entry",
		fields=[
			"creation",
			"warehouse",
			"item_code",
			"stock_uom",
			"voucher_qty",
			"reserved_qty",
			"delivered_qty",
			"available_qty",
			"voucher_type",
			"voucher_no",
			"from_voucher_type",
			"from_voucher_no",
			"name as stock_reservation_entry",
			"status",
			"project",
			"company",
		],
		filters=query_filters,
		limit_page_length=0,
		as_list=True,
	)
	rows = []
	for row in data:
		row = list(row)
		row[7] = row[7] - row[5] if row[7] is not None and row[5] is not None else None
		rows.append(row)
	return rows


def get_columns():
	columns = [
		{
			"label": _("Date"),
			"fieldname": "date",
			"fieldtype": "Datetime",
			"width": 150,
		},
		{
			"fieldname": "warehouse",
			"label": _("Warehouse"),
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 150,
		},
		{
			"fieldname": "item_code",
			"label": _("Item"),
			"fieldtype": "Link",
			"options": "Item",
			"width": 100,
		},
		{
			"fieldname": "stock_uom",
			"label": _("Stock UOM"),
			"fieldtype": "Link",
			"options": "UOM",
			"width": 100,
		},
		{
			"fieldname": "voucher_qty",
			"label": _("Voucher Qty"),
			"fieldtype": "Float",
			"width": 110,
			"convertible": "qty",
		},
		{
			"fieldname": "reserved_qty",
			"label": _("Reserved Qty"),
			"fieldtype": "Float",
			"width": 110,
			"convertible": "qty",
		},
		{
			"fieldname": "delivered_qty",
			"label": _("Delivered Qty"),
			"fieldtype": "Float",
			"width": 110,
			"convertible": "qty",
		},
		{
			"fieldname": "available_qty",
			"label": _("Available Qty to Reserve"),
			"fieldtype": "Float",
			"width": 120,
			"convertible": "qty",
		},
		{
			"fieldname": "voucher_type",
			"label": _("Voucher Type"),
			"fieldtype": "Data",
			"width": 110,
		},
		{
			"fieldname": "voucher_no",
			"label": _("Voucher No"),
			"fieldtype": "Dynamic Link",
			"options": "voucher_type",
			"width": 120,
		},
		{
			"fieldname": "from_voucher_type",
			"label": _("From Voucher Type"),
			"fieldtype": "Data",
			"width": 110,
		},
		{
			"fieldname": "from_voucher_no",
			"label": _("From Voucher No"),
			"fieldtype": "Dynamic Link",
			"options": "from_voucher_type",
			"width": 120,
		},
		{
			"fieldname": "stock_reservation_entry",
			"label": _("Stock Reservation Entry"),
			"fieldtype": "Link",
			"options": "Stock Reservation Entry",
			"width": 150,
		},
		{
			"fieldname": "status",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"fieldname": "project",
			"label": _("Project"),
			"fieldtype": "Link",
			"options": "Project",
			"width": 100,
		},
		{
			"fieldname": "company",
			"label": _("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"width": 110,
		},
	]

	return columns
