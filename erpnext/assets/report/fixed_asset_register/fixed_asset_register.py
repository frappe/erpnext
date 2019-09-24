# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data

def get_columns(filters):
	return [
		{
			"label": _("Asset Id"),
			"fieldtype": "Link",
			"fieldname": "asset_id",
			"options": "Asset",
			"width": 100
		},
		{
			"label": _("Asset Name"),
			"fieldtype": "Data",
			"fieldname": "asset_name",
			"width": 140
		},
		{
			"label": _("Asset Category"),
			"fieldtype": "Link",
			"fieldname": "asset_category",
			"options": "Asset Category",
			"width": 100
		},
		{
			"label": _("Business Unit"),
			"fieldtype": "Data",
			"fieldname": "business_unit",
			"width": 100
		},
		{
			"label": _("Department"),
			"fieldtype": "Link",
			"fieldname": "department",
			"options": "Department",
			"width": 100
		},
		{
			"label": _("Location"),
			"fieldtype": "Link",
			"fieldname": "location",
			"options": "Location",
			"width": 100
		},
		{
			"label": _("Purchase Date"),
			"fieldtype": "Date",
			"fieldname": "purchase_date",
			"width": 90
		},
		{
			"label": _("Gross Purchase Amount"),
			"fieldname": "gross_purchase_amount",
			"options": "Currency",
			"width": 90
		},
		{
			"label": _("Vendor Name"),
			"fieldtype": "Data",
			"fieldname": "vendor_name",
			"width": 100
		},
		{
			"label": _("Available For Use Date"),
			"fieldtype": "Date",
			"fieldname": "available_for_use_date",
			"width": 90
		},
		{
			"label": _("Current Value"),
			"fieldname": "current_value",
			"options": "Currency",
			"width": 90
		},
	]

def get_conditions(filters):
	conditions = {}

	if filters.company:
		conditions["company"] = filters.company

	return conditions

def get_data(filters):

	data = []

	conditions = get_conditions(filters)
	current_value_map = get_finance_book_value_map(filters.finance_book)
	print(current_value_map)

	assets_record = frappe.db.get_all("Asset",
		filters=conditions,
		fields=["name", "asset_name", "department", "cost_center",
			"asset_category", "location", "purchase_date", "supplier",
			"gross_purchase_amount", "available_for_use_date"])

	for asset in assets_record:
		row = {
			"asset_id": asset.name,
			"asset_name": asset.asset_name,
			"department": asset.department,
			"business_unit": asset.cost_center,
			"vendor_name": asset.supplier,
			"gross_purchase_amount": asset.gross_purchase_amount,
			"available_for_use_date": asset.available_for_use_date,
			"location": asset.location,
			"asset_category": asset.asset_category,
			"purchase_date": asset.purchase_date,
			"current_value": current_value_map.get(asset.name)
		}
		data.append(row)

	return data

def get_finance_book_value_map(finance_book=''):
	return frappe._dict(frappe.db.sql(''' Select
		parent, value_after_depreciation
		FROM `tabAsset Finance Book`
		WHERE
			parentfield='finance_books'
			AND finance_book=%s''', (finance_book), debug=1))