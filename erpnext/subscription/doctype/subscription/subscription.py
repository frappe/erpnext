# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import getdate, add_days, cstr, today
from erpnext.controllers.recurring_document import send_notification, get_next_date
from frappe.model.document import Document

month_map = {'Monthly': 1, 'Quarterly': 3, 'Half-yearly': 6, 'Yearly': 12}
class Subscription(Document):
	def validate(self):
		self.update_status()

	def before_submit(self):
		self.set_next_schedule_date()

	def on_submit(self):
		self.update_subscription_id()
		self.update_status()

	def set_next_schedule_date(self):
		self.next_schedule_date = get_next_schedule_date(self.start_date,
			self.frequency, self.repeat_on_day)

	def update_subscription_id(self):
		frappe.db.set_value(self.base_doctype, self.base_docname, 'subscription', self.name)

	def update_status(self):
		status = {
			'0': 'Draft',
			'1': 'Submitted',
			'2': 'Cancelled'
		}[cstr(self.docstatus or 0)]

		self.db_set("status", status)

def get_next_schedule_date(start_date, frequency, repeat_on_day):
	mcount = month_map.get(frequency)
	if mcount:
		next_date = get_next_date(start_date, mcount, repeat_on_day)
	else:
		days = 7 if frequency == 'Weekly' else 1
		next_date = add_days(start_date, days)
	return next_date

def make_subscription_entry(date=None):
	date = date or today()
	for data in get_subscription_entries(date):
		schedule_date = getdate(data.next_schedule_date)
		while schedule_date <= getdate(today()):
			create_documents(data, schedule_date)

			schedule_date = get_next_schedule_date(schedule_date,
				data.frequency, data.repeat_on_day)

		if schedule_date:
			frappe.db.set_value('Subscription', data.name, 'next_schedule_date', schedule_date)

def get_subscription_entries(date):
	return frappe.db.sql(""" select * from `tabSubscription`
		where docstatus = 1 and next_schedule_date <=%s
			and base_docname is not null and base_docname != ''
			and next_schedule_date <= ifnull(end_date, '2199-12-31')
			and ifnull(disabled, 0) = 0""", (date), as_dict=1)

def create_documents(data, schedule_date):
	try:
		doc = make_new_document(data, schedule_date)
		if data.notify_by_email:
			send_notification(doc, data.print_format, data.recipients)
	except Exception:
		frappe.log_error(frappe.get_traceback())

def make_new_document(args, schedule_date):
	doc = frappe.get_doc(args.base_doctype, args.base_docname)
	new_doc = frappe.copy_doc(doc, ignore_no_copy=False)
	update_doc(new_doc, args, schedule_date)
	new_doc.insert(ignore_permissions=True)

	if args.submit_on_creation:
		new_doc.submit()

	return new_doc

def update_doc(new_document, args, schedule_date):
	new_document.docstatus = 0
	if new_document.meta.get_field('set_posting_time'):
		new_document.set('set_posting_time', 1)

	if new_document.meta.get_field('subscription'):
		new_document.set('subscription', args.name)

	for data in new_document.meta.fields:
		if data.fieldtype == 'Date' and data.reqd==1:
			new_document.set(data.fieldname, schedule_date)

@frappe.whitelist()
def make_subscription(doctype, docname):
	doc = frappe.new_doc('Subscription')
	doc.base_doctype = doctype
	doc.base_docname = docname
	return doc
