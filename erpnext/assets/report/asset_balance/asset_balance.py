# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder.functions import Sum

def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data

def get_data(filters):
	posting_date = filters.get("till_date")

	gl_entry = frappe.qb.DocType("GL Entry")
	asset = frappe.qb.DocType("Asset")
	depreciation_total = Sum(gl_entry.debit).as_("depreciation_total")
	query = (
		frappe.qb.from_(gl_entry)
		.inner_join(asset)
		.on(asset.name == gl_entry.against_voucher)
		.select(
			gl_entry.against_voucher.as_("asset"), 
			asset.asset_name, asset.asset_category, 
			depreciation_total, 
			asset.gross_purchase_amount,
			(asset.gross_purchase_amount-depreciation_total).as_("balance")
			)
		.where(
			(gl_entry.against_voucher_type=="Asset")
			& (gl_entry.posting_date<="{posting_date}".format(posting_date=posting_date))
		)
		.groupby(gl_entry.against_voucher)
	)
	
	if filters.get("asset"):
		query.where(gl_entry.against_voucher==filters.get("asset"))
	return query.run(as_dict=True)

def get_columns(filters):
	"""
	Get columns from data
	"""
	return [
		{
			"label": _("Asset"),
			"fieldname": "asset",
			"fieldtype": "Link",
			"options": "Asset",
			"hidden": 1 if filters.get("asset_category_enbale") else 0,
			"width": 140
		},
		{
			"label": _("Asset Name"),
			"fieldname": "asset_name",
			"fieldtype": "Data",
			"hidden": 1 if filters.get("asset_category_enbale") else 0,
			"width": 300
		},
		{
			"label": _("Asset Category"),
			"fieldname": "asset_category",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"label": _("Purchase Amount"),
			"fieldname": "gross_purchase_amount",
			"fieldtype": "Currency",
			"width": 140
		},
		{
			"label": _("Depreciation Total"),
			"fieldname": "depreciation_total",
			"fieldtype": "Currency",
			"width": 140
		},
		{
			"label": _("Balance"),
			"fieldname": "balance",
			"fieldtype": "Currency",
			"width": 140
		}
	]
