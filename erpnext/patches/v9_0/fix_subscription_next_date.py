# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doctype('Subscription')

	doctypes = ('Purchase Order', 'Sales Order', 'Purchase Invoice', 'Sales Invoice')
	for data in frappe.get_all('Subscription', fields = ["name", "reference_doctype", "reference_document"],
		filters = {'reference_doctype': ('in', doctypes)}):
		doc = frappe.get_doc('Subscription', data.name)
		fields = ['transaction_date']
		if doc.reference_doctype in ['Sales Invoice', 'Purchase Invoice']:
			fields = ['posting_date']

		fields.extend(['from_date', 'to_date'])
		reference_data = frappe.db.get_value(data.reference_doctype,
			data.reference_document, fields, as_dict=1)

		if reference_data:
			doc.start_date = reference_data.get('posting_date') or reference_data.get('transaction_date')
			doc.from_date = reference_data.get('from_date')
			doc.to_date = reference_data.get('to_date')
			doc.set_next_schedule_date()
			doc.db_update()