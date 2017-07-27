# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	columns, data = get_columns(), get_data(filters)
	return columns, data
	
def get_data(filters):
	data = frappe.db.sql("""
		select 
			a.name as asset, a.asset_category, a.status, 
			a.depreciation_method, a.purchase_date, a.gross_purchase_amount,
			ds.schedule_date as depreciation_date, ds.depreciation_amount, 
			ds.accumulated_depreciation_amount, 
			(a.gross_purchase_amount - ds.accumulated_depreciation_amount) as amount_after_depreciation,
			ds.journal_entry as depreciation_entry
		from
			`tabAsset` a, `tabDepreciation Schedule` ds
		where
			a.name = ds.parent
			and a.docstatus=1
			and ifnull(ds.journal_entry, '') != ''
			and ds.schedule_date between %(from_date)s and %(to_date)s
			and a.company = %(company)s
			{conditions}
		order by
			a.name asc, ds.schedule_date asc
	""".format(conditions=get_filter_conditions(filters)), filters, as_dict=1)
		
	return data
	
def get_filter_conditions(filters):
	conditions = ""
	
	if filters.get("asset"):
		conditions += " and a.name = %(asset)s"
	
	if filters.get("asset_category"):
		conditions += " and a.asset_category = %(asset_category)s"
		
	return conditions
	
def get_columns():
	return [
		{
			"label": _("Asset"),
			"fieldname": "asset",
			"fieldtype": "Link",
			"options": "Asset",
			"width": 120
		},
		{
			"label": _("Depreciation Date"),
			"fieldname": "depreciation_date",
			"fieldtype": "Date",
			"width": 120
		},
		{
			"label": _("Purchase Amount"),
			"fieldname": "gross_purchase_amount",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"label": _("Depreciation Amount"),
			"fieldname": "depreciation_amount",
			"fieldtype": "Currency",
			"width": 140
		},
		{
			"label": _("Accumulated Depreciation Amount"),
			"fieldname": "accumulated_depreciation_amount",
			"fieldtype": "Currency",
			"width": 210
		},
		{
			"label": _("Amount After Depreciation"),
			"fieldname": "amount_after_depreciation",
			"fieldtype": "Currency",
			"width": 180
		},
		{
			"label": _("Depreciation Entry"),
			"fieldname": "depreciation_entry",
			"fieldtype": "Link",
			"options": "Journal Entry",
			"width": 140
		},
		{
			"label": _("Asset Category"),
			"fieldname": "asset_category",
			"fieldtype": "Link",
			"options": "Asset Category",
			"width": 120
		},
		{
			"label": _("Current Status"),
			"fieldname": "status",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": _("Depreciation Method"),
			"fieldname": "depreciation_method",
			"fieldtype": "Data",
			"width": 130
		},
		{
			"label": _("Purchase Date"),
			"fieldname": "purchase_date",
			"fieldtype": "Date",
			"width": 120
		}
	]
