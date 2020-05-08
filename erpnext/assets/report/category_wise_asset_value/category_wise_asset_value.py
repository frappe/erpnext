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

def get_conditions(filters):
	conditions = { 'docstatus': 1 }

	if filters.get('company'):
		conditions["company"] = filters.company
	if filters.get('purchase_date'):
		conditions["purchase_date"] = ('<=', filters.get('purchase_date'))
	if filters.get('available_for_use_date'):
		conditions["available_for_use_date"] = ('<=', filters.get('available_for_use_date'))
	if filters.get('is_existing_asset'):
		conditions["is_existing_asset"] = filters.get('is_existing_asset')
	if filters.get('cost_center'):
		conditions["cost_center"] = filters.get('cost_center')

	return conditions

def get_data(filters):

	data = []
	depreciation_amount_map = get_finance_book_value_map(filters)

	assets_record = frappe.db.get_all("Asset",
		filters=get_conditions(filters),
		fields=["name", "asset_name", "asset_category", "gross_purchase_amount",
		"opening_accumulated_depreciation", "available_for_use_date", "purchase_date"],
		group_by="asset_category")

	for asset in assets_record:
		asset_value = asset.gross_purchase_amount - flt(asset.opening_accumulated_depreciation) \
			- flt(depreciation_amount_map.get(asset.name))
		if asset_value:
			row = {
				"asset_category": asset.asset_category,
				"asset_id": asset.name,
				"asset_name": asset.asset_name,
				"purchase_date": asset.purchase_date,
				"available_for_use_date": asset.available_for_use_date,
				"gross_purchase_amount": asset.gross_purchase_amount,
				"opening_accumulated_depreciation": asset.opening_accumulated_depreciation,
				"depreciated_amount": depreciation_amount_map.get(asset.name) or 0.0,
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

def get_columns(filters):
	return [
		{
			"label": _("Asset Category"),
			"fieldtype": "Link",
			"fieldname": "asset_category",
			"options": "Asset Category",
			"width": 120
		},
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
			"fieldtype": "Currency",
			"options": "company:currency",
			"width": 100
		},
		{
			"label": _("Opening Accumulated Depreciation"),
			"fieldname": "opening_accumulated_depreciation",
			"fieldtype": "Currency",
			"options": "company:currency",
			"width": 90
		},
		{
			"label": _("Depreciated Amount"),
			"fieldname": "depreciated_amount",
			"fieldtype": "Currency",
			"options": "company:currency",
			"width": 100
		},
		{
			"label": _("Asset Value"),
			"fieldname": "asset_value",
			"fieldtype": "Currency",
			"options": "company:currency",
			"width": 100
		}
	]