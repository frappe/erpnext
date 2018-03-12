# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import calendar
from frappe import _
from frappe.desk.form import assign_to
from frappe.utils.jinja import validate_template
from dateutil.relativedelta import relativedelta
from frappe.utils.user import get_system_managers
from frappe.utils import cstr, getdate, split_emails, add_days, today, get_last_day, get_first_day
from frappe.model.document import Document

month_map = {'Monthly': 1, 'Quarterly': 3, 'Half-yearly': 6, 'Yearly': 12}
class Subscription(Document):
	def validate(self):
		self.update_status()
		self.validate_reference_doctype()
		self.validate_dates()
		self.validate_next_schedule_date()
		self.validate_email_id()

		validate_template(self.subject or "")
		validate_template(self.message or "")

	def before_submit(self):
		if not self.next_schedule_date:
			self.next_schedule_date = get_next_schedule_date(self.start_date,
				self.frequency, self.repeat_on_day)

	def on_submit(self):
		self.update_subscription_id()

	def on_update_after_submit(self):
		self.validate_dates()
		self.set_next_schedule_date()

	def before_cancel(self):
		self.unlink_subscription_id()
		self.next_schedule_date = None

	def unlink_subscription_id(self):
		frappe.db.sql("update `tab{0}` set subscription = null where subscription=%s"
			.format(self.reference_doctype), self.name)

	def validate_reference_doctype(self):
		if not frappe.get_meta(self.reference_doctype).has_field('subscription'):
			frappe.throw(_("Add custom field Subscription in the doctype {0}").format(self.reference_doctype))

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
		if self.repeat_on_day:
			self.next_schedule_date = get_next_date(self.next_schedule_date, 0, self.repeat_on_day)

	def update_subscription_id(self):
		frappe.db.set_value(self.reference_doctype, self.reference_document, "subscription", self.name)

	def update_status(self, status=None):
		self.status = {
			'0': 'Draft',
			'1': 'Submitted',
			'2': 'Cancelled'
		}[cstr(self.docstatus or 0)]

		if status and status != 'Resumed':
			self.status = status

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

			if schedule_date and not frappe.db.get_value('Subscription', data.name, 'disabled'):
				frappe.db.set_value('Subscription', data.name, 'next_schedule_date', schedule_date)

def get_subscription_entries(date):
	return frappe.db.sql(""" select * from `tabSubscription`
		where docstatus = 1 and next_schedule_date <=%s
			and reference_document is not null and reference_document != ''
			and next_schedule_date <= ifnull(end_date, '2199-12-31')
			and ifnull(disabled, 0) = 0 and status != 'Stopped' """, (date), as_dict=1)

def create_documents(data, schedule_date):
	try:
		doc = make_new_document(data, schedule_date)
		if data.notify_by_email and data.recipients:
			print_format = data.print_format or "Standard"
			send_notification(doc, data, print_format=print_format)

		frappe.db.commit()
	except Exception:
		frappe.db.rollback()
		frappe.db.begin()
		frappe.log_error(frappe.get_traceback())
		disable_subscription(data)
		frappe.db.commit()
		if data.reference_document and not frappe.flags.in_test:
			notify_error_to_user(data)

def disable_subscription(data):
	subscription = frappe.get_doc('Subscription', data.name)
	subscription.db_set('disabled', 1)

def notify_error_to_user(data):
	party = ''
	party_type = ''

	if data.reference_doctype in ['Sales Order', 'Sales Invoice', 'Delivery Note']:
		party_type = 'customer'
	elif data.reference_doctype in ['Purchase Order', 'Purchase Invoice', 'Purchase Receipt']:
		party_type = 'supplier'

	if party_type:
		party = frappe.db.get_value(data.reference_doctype, data.reference_document, party_type)

	notify_errors(data.reference_document, data.reference_doctype, party, data.owner, data.name)

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

	mcount = month_map.get(args.frequency)

	if new_document.meta.get_field('subscription'):
		new_document.set('subscription', args.name)

	for fieldname in ['naming_series', 'ignore_pricing_rule', 'posting_time'
		'select_print_heading', 'remarks', 'owner']:
		if new_document.meta.get_field(fieldname):
			new_document.set(fieldname, reference_doc.get(fieldname))

	# copy item fields
	if new_document.meta.get_field('items'):
		for i, item in enumerate(new_document.items):
			for fieldname in ("page_break",):
				item.set(fieldname, reference_doc.items[i].get(fieldname))

	for data in new_document.meta.fields:
		if data.fieldtype == 'Date' and data.reqd:
			new_document.set(data.fieldname, schedule_date)

	set_subscription_period(args, mcount, new_document)

	new_document.run_method("on_recurring", reference_doc=reference_doc, subscription_doc=args)

def set_subscription_period(args, mcount, new_document):
	if mcount and new_document.meta.get_field('from_date') and new_document.meta.get_field('to_date'):
		last_ref_doc = frappe.db.sql("""
			select name, from_date, to_date
			from `tab{0}`
			where subscription=%s and docstatus < 2
			order by creation desc
			limit 1
		""".format(args.reference_doctype), args.name, as_dict=1)

		if not last_ref_doc:
			return

		from_date = get_next_date(last_ref_doc[0].from_date, mcount)

		if (cstr(get_first_day(last_ref_doc[0].from_date)) == cstr(last_ref_doc[0].from_date)) and \
			(cstr(get_last_day(last_ref_doc[0].to_date)) == cstr(last_ref_doc[0].to_date)):
				to_date = get_last_day(get_next_date(last_ref_doc[0].to_date, mcount))
		else:
			to_date = get_next_date(last_ref_doc[0].to_date, mcount)

		new_document.set('from_date', from_date)
		new_document.set('to_date', to_date)

def get_next_date(dt, mcount, day=None):
	dt = getdate(dt)
	dt += relativedelta(months=mcount, day=day)

	return dt

def send_notification(new_rv, subscription_doc, print_format='Standard'):
	"""Notify concerned persons about recurring document generation"""
	print_format = print_format
	subject = subscription_doc.subject or ''
	message = subscription_doc.message or ''

	if not subscription_doc.subject:
		subject = _("New {0}: #{1}").format(new_rv.doctype, new_rv.name)
	elif "{" in subscription_doc.subject:
		subject = frappe.render_template(subscription_doc.subject, {'doc': new_rv})

	if not subscription_doc.message:
		message = _("Please find attached {0} #{1}").format(new_rv.doctype, new_rv.name)
	elif "{" in subscription_doc.message:
		message = frappe.render_template(subscription_doc.message, {'doc': new_rv})

	attachments = [frappe.attach_print(new_rv.doctype, new_rv.name,
		file_name=new_rv.name, print_format=print_format)]

	frappe.sendmail(subscription_doc.recipients,
		subject=subject, message=message, attachments=attachments)

def notify_errors(doc, doctype, party, owner, name):
	recipients = get_system_managers(only_name=True)
	frappe.sendmail(recipients + [frappe.db.get_value("User", owner, "email")],
		subject=_("[Urgent] Error while creating recurring %s for %s" % (doctype, doc)),
		message = frappe.get_template("templates/emails/recurring_document_failed.html").render({
			"type": _(doctype),
			"name": doc,
			"party": party or "",
			"subscription": name
		}))

	assign_task_to_owner(name, "Recurring Documents Failed", recipients)

def assign_task_to_owner(name, msg, users):
	for d in users:
		args = {
			'doctype'		:	'Subscription',
			'assign_to' 	:	d,
			'name'			:	name,
			'description'	:	msg,
			'priority'		:	'High'
		}
		assign_to.add(args)

@frappe.whitelist()
def make_subscription(doctype, docname):
	doc = frappe.new_doc('Subscription')

	reference_doc = frappe.get_doc(doctype, docname)
	doc.reference_doctype = doctype
	doc.reference_document = docname
	doc.start_date = reference_doc.get('posting_date') or reference_doc.get('transaction_date')
	return doc

@frappe.whitelist()
def stop_resume_subscription(subscription, status):
	doc = frappe.get_doc('Subscription', subscription)
	frappe.msgprint(_("Subscription has been {0}").format(status))
	if status == 'Resumed':
		doc.next_schedule_date = get_next_schedule_date(today(),
			doc.frequency, doc.repeat_on_day)

	doc.update_status(status)
	doc.save()

	return doc.status

def subscription_doctype_query(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql("""select parent from `tabDocField`
		where fieldname = 'subscription'
			and parent like %(txt)s
		order by
			if(locate(%(_txt)s, parent), locate(%(_txt)s, parent), 99999),
			parent
		limit %(start)s, %(page_len)s""".format(**{
			'key': searchfield,
		}), {
			'txt': "%%%s%%" % txt,
			'_txt': txt.replace("%", ""),
			'start': start,
			'page_len': page_len
		})