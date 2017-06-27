# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from erpnext.accounts.report.sales_register.sales_register import _execute

def execute(filters=None):
	return _execute(filters, additional_table_columns=[
		dict(fieldtype='Data', label='Customer GSTIN', width=120),
		dict(fieldtype='Data', label='Company GSTIN', width=120)
	], additional_query_columns=[
		'customer_gstin',
		'company_gstin'
	])
