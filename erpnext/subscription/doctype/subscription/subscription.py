# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe.utils import getdate, add_days, cstr, today
from erpnext.controllers.recurring_document import send_notification
from frappe.model.document import Document

month_map = {'Monthly': 1, 'Quarterly': 3, 'Half-yearly': 6, 'Yearly': 12}
class Subscription(Document):
	def validate(self):
		self.update_status()

	def before_submit(self):
		self.create_schedule()
		self.update_subscription_id()

	def create_schedule(self):
		self.set('schedules', [])
		schedule_date = getdate(self.start_date)
		while schedule_date <= getdate(self.end_date):
			next_schedule_date = self.add_schedule(schedule_date)
			schedule_date = next_schedule_date

	def add_schedule(self, schedule_date):
		if schedule_date:
			next_schedule_date = self.get_next_schedule_date(schedule_date)
			docname = self.base_docname \
				if getdate(self.start_date) == getdate(schedule_date) else None

			self.append('schedules', {
				'schedule_date': schedule_date,
				'base_doctype': self.base_doctype,
				'base_docname': docname,
				'next_schedule_date': next_schedule_date
			})

		return next_schedule_date
		
	def update_subscription_id(self):
		frappe.db.set_value(self.base_doctype, self.base_docname, 'subscription', self.name)

	def get_next_schedule_date(self, start_date):
		mcount = month_map.get(self.frequency)
		if mcount:
			next_date = get_next_date(start_date, mcount, self.repeat_on_day)
		else:
			days = 7 if self.frequency == 'Weekly' else 1
			next_date = add_days(start_date, days)
		return next_date

	def on_submit(self):
		self.update_status()

	def update_status(self):
		status = {
			'0': 'Draft',
			'1': 'Submitted',
			'2': 'Cancelled'
		}[cstr(self.docstatus or 0)]

		self.db_set("status", status)

def get_next_date(dt, mcount, day=None):
	dt = getdate(dt)

	from dateutil.relativedelta import relativedelta
	dt += relativedelta(months=mcount, day=day)

	return dt

def make_subscription_entry(date=None):
	date = date or today()
	for data in get_subscription_entries(date):
		try:
			doc = make_new_document(data)
			if doc.name:
				update_subscription_document(data.name, doc.name)

			if data.notify_by_email:
				send_notification(doc, data.print_format, data.recipients)
		except:
			frappe.log_error(frappe.get_traceback())

def get_subscription_entries(date):
	return frappe.db.sql(""" select sc.name as subscription, sc.base_doctype, sc.base_docname,
			sc.submit_on_creation, sc.notify_by_email, sc.recipients, sc.print_format, scs.schedule_date, scs.name
		from `tabSubscription` as sc, `tabSubscription Schedule` as scs
		where sc.name = scs.parent and sc.docstatus = 1 and scs.schedule_date <=%s
			and scs.base_docname is null and ifnull(sc.disabled, 0) = 0""", (date), as_dict=1)

def make_new_document(args):
	doc = frappe.get_doc(args.base_doctype, args.base_docname)
	new_doc = frappe.copy_doc(doc, ignore_no_copy=False)
	update_doc(new_doc, args)
	new_doc.insert(ignore_permissions=True)

	if args.submit_on_creation:
		new_doc.submit()

	return new_doc

def update_doc(new_document, args):
	new_document.docstatus = 0
	if new_document.meta.get_field('set_posting_time'):
		new_document.set('set_posting_time', 1)

	if new_document.meta.get_field('subscription'):
		new_document.set('subscription', args.subscription)

	for data in new_document.meta.fields:
		if data.fieldtype == 'Date' and data.reqd==1:
			new_document.set(data.fieldname, args.schedule_date)

def update_subscription_document(name, docname):
	frappe.db.sql(""" update `tabSubscription Schedule` set base_docname = %s
		where name = %s""", (docname, name))
