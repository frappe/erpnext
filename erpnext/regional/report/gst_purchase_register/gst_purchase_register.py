# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from erpnext.accounts.report.purchase_register.purchase_register import _execute

def execute(filters=None):
	return _execute(filters, additional_table_columns=[
		dict(fieldtype='Data', label='Supplier GSTIN', fieldname="supplier_gstin", width=120),
		dict(fieldtype='Data', label='Company GSTIN', fieldname="company_gstin", width=120),
		dict(fieldtype='Data', label='Reverse Charge', fieldname="reverse_charge", width=120),
		dict(fieldtype='Data', label='Invoice Type', fieldname="invoice_type", width=120),
		dict(fieldtype='Data', label='Export Type', fieldname="export_type", width=120),
		dict(fieldtype='Data', label='E-Commerce GSTIN', fieldname="ecommerce_gstin", width=130)
	], additional_query_columns=[
		'supplier_gstin',
		'company_gstin',
		'reverse_charge',
		'invoice_type',
		'export_type',
		'ecommerce_gstin'
	])

