# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _


def execute(filters=None):
	if filters.from_date >= filters.to_date:
		frappe.msgprint(_("To Date must be greater than From Date"))

	columns = get_columns(filters)
	data = get_data(filters)

	return columns, data or []


def get_columns(filters):
	return [
		{
			"label": _("Subcontract Order"),
			"fieldtype": "Link",
			"fieldname": "subcontract_order",
			"options": filters.order_type,
			"width": 200,
		},
		{"label": _("Date"), "fieldtype": "Date", "fieldname": "date", "width": 150},
		{
			"label": _("Supplier"),
			"fieldtype": "Link",
			"fieldname": "supplier",
			"options": "Supplier",
			"width": 150,
		},
		{"label": _("Item Code"), "fieldtype": "Data", "fieldname": "rm_item_code", "width": 150},
		{"label": _("Required Quantity"), "fieldtype": "Float", "fieldname": "reqd_qty", "width": 150},
		{
			"label": _("Transferred Quantity"),
			"fieldtype": "Float",
			"fieldname": "transferred_qty",
			"width": 200,
		},
		{"label": _("Pending Quantity"), "fieldtype": "Float", "fieldname": "p_qty", "width": 150},
	]


def get_data(filters):
	order_rm_item_details = get_order_items_to_supply(filters)

	data = []
	for row in order_rm_item_details:
		transferred_qty = row.get("transferred_qty") or 0
		if transferred_qty < row.get("reqd_qty", 0):
			pending_qty = frappe.utils.flt(row.get("reqd_qty", 0) - transferred_qty)
			row.p_qty = pending_qty if pending_qty > 0 else 0
			data.append(row)

	return data


def get_order_items_to_supply(filters):
	supplied_items_table = (
		"Purchase Order Item Supplied"
		if filters.order_type == "Purchase Order"
		else "Subcontracting Order Supplied Item"
	)

	record_filters = [
		[filters.order_type, "per_received", "<", "100"],
		[filters.order_type, "supplier", "=", filters.supplier],
		[filters.order_type, "transaction_date", "<=", filters.to_date],
		[filters.order_type, "transaction_date", ">=", filters.from_date],
		[filters.order_type, "docstatus", "=", 1],
	]

	if filters.order_type == "Purchase Order":
		record_filters.append([filters.order_type, "is_old_subcontracting_flow", "=", 1])

	return frappe.db.get_all(
		filters.order_type,
		fields=[
			"name as subcontract_order",
			"transaction_date as date",
			"supplier as supplier",
			f"`tab{supplied_items_table}`.rm_item_code as rm_item_code",
			f"`tab{supplied_items_table}`.required_qty as reqd_qty",
			f"`tab{supplied_items_table}`.supplied_qty as transferred_qty",
		],
		filters=record_filters,
	)
