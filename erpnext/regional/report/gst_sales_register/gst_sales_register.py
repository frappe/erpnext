# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from erpnext.accounts.report.sales_register.sales_register import _execute

def execute(filters=None):
	return _execute(filters, additional_table_columns=[
		dict(fieldtype='Data', label='Customer GSTIN', width=120),
		dict(fieldtype='Data', label='Billing Address GSTIN', width=140),
		dict(fieldtype='Data', label='Company GSTIN', width=120),
		dict(fieldtype='Data', label='Place of Supply', width=120),
		dict(fieldtype='Data', label='Reverse Charge', width=120),
		dict(fieldtype='Data', label='Invoice Type', width=120),
		dict(fieldtype='Data', label='Export Type', width=120),
		dict(fieldtype='Data', label='E-Commerce GSTIN', width=130)
	], additional_query_columns=[
		'customer_gstin',
		'billing_address_gstin',
		'company_gstin',
		'place_of_supply',
		'reverse_charge',
		'invoice_type',
		'export_type',
		'ecommerce_gstin'
	])
