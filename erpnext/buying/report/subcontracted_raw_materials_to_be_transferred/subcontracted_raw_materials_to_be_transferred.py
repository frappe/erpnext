# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _


def execute(filters=None):
	if filters.from_date >= filters.to_date:
		frappe.msgprint(_("To Date must be greater than From Date"))

	columns = get_columns()
	data = get_data(filters)

	return columns, data or []


def get_columns():
	return [
		{
			"label": _("Purchase Order"),
			"fieldtype": "Link",
			"fieldname": "purchase_order",
			"options": "Purchase Order",
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
	sco_rm_item_details = get_sco_items_to_supply(filters)

	data = []
	for row in sco_rm_item_details:
		transferred_qty = row.get("transferred_qty") or 0
		if transferred_qty < row.get("reqd_qty", 0):
			pending_qty = frappe.utils.flt(row.get("reqd_qty", 0) - transferred_qty)
			row.p_qty = pending_qty if pending_qty > 0 else 0
			data.append(row)

	return data


def get_sco_items_to_supply(filters):
	return frappe.db.get_all(
		"Subcontracting Order",
		fields=[
			"name as subcontracting_order",
			"transaction_date as date",
			"supplier as supplier",
			"`tabSubcontracting Order Supplied Item`.rm_item_code as rm_item_code",
			"`tabSubcontracting Order Supplied Item`.required_qty as reqd_qty",
			"`tabSubcontracting Order Supplied Item`.supplied_qty as transferred_qty",
		],
		filters=[
			["Subcontracting Order", "per_received", "<", "100"],
			["Subcontracting Order", "supplier", "=", filters.supplier],
			["Subcontracting Order", "transaction_date", "<=", filters.to_date],
			["Subcontracting Order", "transaction_date", ">=", filters.from_date],
			["Subcontracting Order", "docstatus", "=", 1],
		],
	)
