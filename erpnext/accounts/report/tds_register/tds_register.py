# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, formatdate, cstr, cint
from erpnext.accounts.doctype.tds_remittance.tds_remittance import get_tds_invoices

def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)

	return columns, data

def get_data(filters):
	validate_filters(filters)
	data = []
	entries = get_tds_invoices(filters.tax_withholding_category, filters.from_date, filters.to_date,
		name = None, filter_existing = False, party_type = filters.party_type)
	for d in entries:
		row = [d.party_type, d.party, d.tpn, d.invoice_type, d.invoice_no, d.posting_date, d.bill_amount, filters.tax_withholding_category, 
			d.tds_amount, d.cost_center, d.remittance_status, d.tds_remittance, d.tds_receipt_update]
		data.append(row)
	return data

def validate_filters(filters):
	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date cannot be greater than To Date"))

def get_columns(filters):
	cols = [
		{
		  "fieldname": "party_type",
		  "label": "Party Type",
		  "fieldtype": "Data",
		  "width": 100,
		},
		{
		  "fieldname": "Party",
		  "label": "Party",
		  "fieldtype": "Dynamic Link",
		  "options":"party_type",
		  "width": 200,
		},
		{
			"fieldname": "tpn",
			"label": "TPN Number",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "invoice_type",
			"label": "Invoice Type",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "invoice_no",
			"label": "Invoice No",
			"fieldtype": "Dynamic Link",
			"options":"invoice_type",
			"width": 200
		},
		{
			"fieldname": "posting_date",
			"label": "Invoice Date",
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "bill_amount",
			"label": "Bill Amount",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "tds_rate",
			"label": "TDS Rate(%)",
			"fieldtype": "Link",
			"options": "Tax Withholding Category",
			"width": 80
		},
		{
			"fieldname": "tds_amount",
			"label": "TDS Amount",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "cost_center",
			"label": "Cost Center",
			"fieldtype": "Link",
			"options": "Cost Center",
			"width": 150
		},
		{
			"fieldname": "remittance_status",
			"label": "Status",
			"fieldtype": "Data",
			"width": 80
		},
		{
			"fieldname": "tds_remittance",
			"label": "Remittance",
			"fieldtype": "Link",
			"options": "TDS Remittance",
			"width": 110
		},
    	{
			"fieldname": "tds_receipt_update",
			"label": "TDS Receipt",
			"fieldtype": "Link",
			"options": "TDS Receipt Update",
			"width": 120
		},	        
	]
	return cols
