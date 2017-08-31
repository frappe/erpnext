# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import calendar
from frappe import _
from frappe.desk.form import assign_to
from dateutil.relativedelta import relativedelta
from frappe.utils.user import get_system_managers
from frappe.utils import cstr, getdate, split_emails, add_days, today
from frappe.model.document import Document

month_map = {'Monthly': 1, 'Quarterly': 3, 'Half-yearly': 6, 'Yearly': 12}
class Subscription(Document):
	def validate(self):
		self.update_status()
		self.validate_dates()
		self.validate_next_schedule_date()
		self.validate_email_id()

	def before_submit(self):
		self.set_next_schedule_date()

	def on_submit(self):
		self.update_subscription_id()

	def on_update_after_submit(self):
		self.validate_dates()
		self.set_next_schedule_date()

	def validate_dates(self):
		if self.end_date and getdate(self.start_date) > getdate(self.end_date):
			frappe.throw(_("End date must be greater than start date"))

	def validate_next_schedule_date(self):
		if self.repeat_on_day and self.next_schedule_date:
			next_date = getdate(self.next_schedule_date)
			if next_date.day != self.repeat_on_day:
				# if the repeat day is the last day of the month (31)
				# and the current month does not have as many days,
				# then the last day of the current month is a valid date
				lastday = calendar.monthrange(next_date.year, next_date.month)[1]
				if self.repeat_on_day < lastday:

					# the specified day of the month is not same as the day specified
					# or the last day of the month
					frappe.throw(_("Next Date's day and Repeat on Day of Month must be equal"))

	def validate_email_id(self):
		if self.notify_by_email:
			if self.recipients:
				email_list = split_emails(self.recipients.replace("\n", ""))

				from frappe.utils import validate_email_add
				for email in email_list:
					if not validate_email_add(email):
						frappe.throw(_("{0} is an invalid email address in 'Recipients'").format(email))
			else:
				frappe.throw(_("'Recipients' not specified"))

	def set_next_schedule_date(self):
		self.next_schedule_date = get_next_schedule_date(self.start_date,
			self.frequency, self.repeat_on_day)

	def update_subscription_id(self):
		doc = frappe.get_doc(self.reference_doctype, self.reference_document)
		if not doc.meta.get_field('subscription'):
			frappe.throw(_("Add custom field Subscription Id in the doctype {0}").format(self.reference_doctype))

		doc.db_set('subscription', self.name)

	def update_status(self):
		self.status = {
			'0': 'Draft',
			'1': 'Submitted',
			'2': 'Cancelled'
		}[cstr(self.docstatus or 0)]

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
			and reference_document is not null and reference_document != ''
			and next_schedule_date <= ifnull(end_date, '2199-12-31')
			and ifnull(disabled, 0) = 0""", (date), as_dict=1)

def create_documents(data, schedule_date):
	try:
		doc = make_new_document(data, schedule_date)
		if data.notify_by_email:
			send_notification(doc, data.print_format, data.recipients)

		frappe.db.commit()
	except Exception:
		frappe.db.rollback()
		frappe.db.begin()
		frappe.log_error(frappe.get_traceback())
		frappe.db.commit()
		if data.reference_document and not frappe.flags.in_test:
			notify_error_to_user(data)

def notify_error_to_user(data):
	party = ''
	party_type = ''

	if data.reference_doctype in ['Sales Order', 'Sales Invoice', 'Delivery Note']:
		party_type = 'customer'
	elif data.reference_doctype in ['Purchase Order', 'Purchase Invoice', 'Purchase Receipt']:
		party_type = 'supplier'

	if party_type:
		party = frappe.db.get_value(data.reference_doctype, data.reference_document, party_type)

	notify_errors(data.reference_document, data.reference_doctype, party, data.owner)

def make_new_document(args, schedule_date):
	doc = frappe.get_doc(args.reference_doctype, args.reference_document)
	new_doc = frappe.copy_doc(doc, ignore_no_copy=False)
	update_doc(new_doc, doc , args, schedule_date)
	new_doc.insert(ignore_permissions=True)

	if args.submit_on_creation:
		new_doc.submit()

	return new_doc

def update_doc(new_document, reference_doc, args, schedule_date):
	new_document.docstatus = 0
	if new_document.meta.get_field('set_posting_time'):
		new_document.set('set_posting_time', 1)

	if new_document.meta.get_field('subscription'):
		new_document.set('subscription', args.name)

	new_document.run_method("on_recurring", reference_doc=reference_doc, subscription_doc=args)
	for data in new_document.meta.fields:
		if data.fieldtype == 'Date' and data.reqd:
			new_document.set(data.fieldname, schedule_date)

def get_next_date(dt, mcount, day=None):
	dt = getdate(dt)
	dt += relativedelta(months=mcount, day=day)

	return dt

def send_notification(new_rv, print_format='Standard', recipients=None):
	"""Notify concerned persons about recurring document generation"""
	recipients = recipients or new_rv.notification_email_address
	print_format = print_format or new_rv.recurring_print_format

	frappe.sendmail(recipients,
		subject=  _("New {0}: #{1}").format(new_rv.doctype, new_rv.name),
		message = _("Please find attached {0} #{1}").format(new_rv.doctype, new_rv.name),
		attachments = [frappe.attach_print(new_rv.doctype, new_rv.name, file_name=new_rv.name, print_format=print_format)])

def notify_errors(doc, doctype, party, owner):
	recipients = get_system_managers(only_name=True)
	frappe.sendmail(recipients + [frappe.db.get_value("User", owner, "email")],
		subject="[Urgent] Error while creating recurring %s for %s" % (doctype, doc),
		message = frappe.get_template("templates/emails/recurring_document_failed.html").render({
			"type": doctype,
			"name": doc,
			"party": party or ""
		}))

	assign_task_to_owner(doc, doctype, "Recurring Invoice Failed", recipients)

def assign_task_to_owner(doc, doctype, msg, users):
	for d in users:
		args = {
			'assign_to' 	:	d,
			'doctype'		:	doctype,
			'name'			:	doc,
			'description'	:	msg,
			'priority'		:	'High'
		}
		assign_to.add(args)

@frappe.whitelist()
def make_subscription(doctype, docname):
	doc = frappe.new_doc('Subscription')
	doc.reference_doctype = doctype
	doc.reference_document = docname
	return doc
