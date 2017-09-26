# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import today

def execute():
	frappe.reload_doc('accounts', 'doctype', 'subscription')
	frappe.reload_doc('selling', 'doctype', 'sales_order')
	frappe.reload_doc('buying', 'doctype', 'purchase_order')
	frappe.reload_doc('accounts', 'doctype', 'sales_invoice')
	frappe.reload_doc('accounts', 'doctype', 'purchase_invoice')

	for doctype in ['Sales Order', 'Sales Invoice',
		'Purchase Invoice', 'Purchase Invoice']:
		for data in get_data(doctype):
			make_subscription(doctype, data)

def get_data(doctype):
	return frappe.db.sql(""" select name, from_date, end_date, recurring_type,recurring_id,
		next_date, notify_by_email, notification_email_address, recurring_print_format,
		repeat_on_day_of_month, submit_on_creation, docstatus
		from `tab{0}` where is_recurring = 1 and next_date >= %s and docstatus < 2
	""".format(doctype), today(), as_dict=1)

def make_subscription(doctype, data):
	doc = frappe.get_doc({
		'doctype': 'Subscription',
		'reference_doctype': doctype,
		'reference_document': data.name,
		'start_date': data.from_date,
		'end_date': data.end_date,
		'frequency': data.recurring_type,
		'repeat_on_day': data.repeat_on_day_of_month,
		'notify_by_email': data.notify_by_email,
		'recipients': data.notification_email_address,
		'next_schedule_date': data.next_date,
		'submit_on_creation': data.submit_on_creation
	}).insert(ignore_permissions=True)

	if data.docstatus == 1:
		doc.submit()