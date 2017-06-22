# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from erpnext.accounts.report.item_wise_purchase_register.item_wise_purchase_register import _execute

def execute(filters=None):
	return _execute(filters, additional_table_columns=[
		dict(fieldtype='Data', label='Supplier GSTIN', width=120),
		dict(fieldtype='Data', label='Company GSTIN', width=120),
		dict(fieldtype='Data', label='HSN Code', width=120)
	], additional_query_columns=[
		'supplier_gstin',
		'company_gstin',
		'gst_hsn_code'
	])
