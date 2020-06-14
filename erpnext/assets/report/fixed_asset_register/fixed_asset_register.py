# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cstr, today, flt

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
			"label": _("Status"),
			"fieldtype": "Data",
			"fieldname": "status",
			"width": 90
		},
		{
			"label": _("Purchase Date"),
			"fieldtype": "Date",
			"fieldname": "purchase_date",
			"width": 90
		},
		{
			"label": _("Available For Use Date"),
			"fieldtype": "Date",
			"fieldname": "available_for_use_date",
			"width": 90
		},
		{
			"label": _("Gross Purchase Amount"),
			"fieldname": "gross_purchase_amount",
			"options": "Currency",
			"width": 90
		},
		{
			"label": _("Asset Value"),
			"fieldname": "asset_value",
			"options": "Currency",
			"width": 90
		},
		{
			"label": _("Opening Accumulated Depreciation"),
			"fieldname": "opening_accumulated_depreciation",
			"options": "Currency",
			"width": 90
		},
		{
			"label": _("Depreciated Amount"),
			"fieldname": "depreciated_amount",
			"options": "Currency",
			"width": 90
		},
		{
			"label": _("Cost Center"),
			"fieldtype": "Link",
			"fieldname": "cost_center",
			"options": "Cost Center",
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
			"label": _("Vendor Name"),
			"fieldtype": "Data",
			"fieldname": "vendor_name",
			"width": 100
		},
		{
			"label": _("Location"),
			"fieldtype": "Link",
			"fieldname": "location",
			"options": "Location",
			"width": 100
		},
	]

def get_conditions(filters):
	conditions = { 'docstatus': 1 }
	status = filters.status
	date = filters.date

	if filters.get('company'):
		conditions["company"] = filters.company
	if filters.get('purchase_date'):
		conditions["purchase_date"] = ('<=', filters.get('purchase_date'))
	if filters.get('available_for_use_date'):
		conditions["available_for_use_date"] = ('<=', filters.get('available_for_use_date'))
	if filters.get('is_existing_asset'):
		conditions["is_existing_asset"] = filters.get('is_existing_asset')
	if filters.get('asset_category'):
		conditions["asset_category"] = filters.get('asset_category')

	# In Store assets are those that are not sold or scrapped
	operand = 'not in'
	if status not in 'In Location':
		operand = 'in'

	conditions['status'] = (operand, ['Sold', 'Scrapped'])

	return conditions

def get_data(filters):

	data = []

	conditions = get_conditions(filters)
	depreciation_amount_map = get_finance_book_value_map(filters)
	pr_supplier_map = get_purchase_receipt_supplier_map()
	pi_supplier_map = get_purchase_invoice_supplier_map()

	assets_record = frappe.db.get_all("Asset",
		filters=conditions,
		fields=["name", "asset_name", "department", "cost_center", "purchase_receipt",
			"asset_category", "purchase_date", "gross_purchase_amount", "location",
			"available_for_use_date", "status", "purchase_invoice", "opening_accumulated_depreciation"])

	for asset in assets_record:
		asset_value = asset.gross_purchase_amount - flt(asset.opening_accumulated_depreciation) \
			- flt(depreciation_amount_map.get(asset.name))
		if asset_value:
			row = {
				"asset_id": asset.name,
				"asset_name": asset.asset_name,
				"status": asset.status,
				"department": asset.department,
				"cost_center": asset.cost_center,
				"vendor_name": pr_supplier_map.get(asset.purchase_receipt) or pi_supplier_map.get(asset.purchase_invoice),
				"gross_purchase_amount": asset.gross_purchase_amount,
				"opening_accumulated_depreciation": asset.opening_accumulated_depreciation,
				"depreciated_amount": depreciation_amount_map.get(asset.name) or 0.0,
				"available_for_use_date": asset.available_for_use_date,
				"location": asset.location,
				"asset_category": asset.asset_category,
				"purchase_date": asset.purchase_date,
				"asset_value": asset_value
			}
			data.append(row)

	return data

def get_finance_book_value_map(filters):
	date = filters.get('purchase_date') or filters.get('available_for_use_date') or today()

	return frappe._dict(frappe.db.sql(''' Select
		parent, SUM(depreciation_amount)
		FROM `tabDepreciation Schedule`
		WHERE
			parentfield='schedules'
			AND schedule_date<=%s
			AND journal_entry IS NOT NULL
			AND ifnull(finance_book, '')=%s
		GROUP BY parent''', (date, cstr(filters.finance_book or ''))))

def get_purchase_receipt_supplier_map():
	return frappe._dict(frappe.db.sql(''' Select
		pr.name, pr.supplier
		FROM `tabPurchase Receipt` pr, `tabPurchase Receipt Item` pri
		WHERE
			pri.parent = pr.name
			AND pri.is_fixed_asset=1
			AND pr.docstatus=1
			AND pr.is_return=0'''))

def get_purchase_invoice_supplier_map():
	return frappe._dict(frappe.db.sql(''' Select
		pi.name, pi.supplier
		FROM `tabPurchase Invoice` pi, `tabPurchase Invoice Item` pii
		WHERE
			pii.parent = pi.name
			AND pii.is_fixed_asset=1
			AND pi.docstatus=1
			AND pi.is_return=0'''))
