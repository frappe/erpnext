# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from erpnext.accounts.report.item_wise_purchase_register.item_wise_purchase_register import _execute

def execute(filters=None):
	return _execute(filters, additional_table_columns=[
		dict(fieldtype='Data', label='Supplier GSTIN', fieldname="supplier_gstin", width=120),
		dict(fieldtype='Data', label='Company GSTIN', fieldname="company_gstin", width=120),
		dict(fieldtype='Data', label='Reverse Charge', fieldname="reverse_charge", width=120),
		dict(fieldtype='Data', label='GST Category', fieldname="gst_category", width=120),
		dict(fieldtype='Data', label='Export Type', fieldname="export_type", width=120),
		dict(fieldtype='Data', label='E-Commerce GSTIN', fieldname="ecommerce_gstin", width=130),
		dict(fieldtype='Data', label='HSN Code', fieldname="gst_hsn_code", width=120),
		dict(fieldtype='Data', label='Supplier Invoice No', fieldname="bill_no", width=120),
		dict(fieldtype='Date', label='Supplier Invoice Date', fieldname="bill_date", width=100)
	], additional_query_columns=[
		'supplier_gstin',
		'company_gstin',
		'reverse_charge',
		'gst_category',
		'export_type',
		'ecommerce_gstin',
		'gst_hsn_code',
		'bill_no',
		'bill_date'
	])
