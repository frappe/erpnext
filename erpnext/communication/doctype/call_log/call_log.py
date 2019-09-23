# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from erpnext.crm.doctype.utils import get_scheduled_employees_for_popup, strip_number
from frappe.contacts.doctype.contact.contact import get_contact_with_phone_number
from erpnext.crm.doctype.lead.lead import get_lead_with_phone_number

class CallLog(Document):
	def before_insert(self):
		number = strip_number(self.get('from'))
		self.contact = get_contact_with_phone_number(number)
		self.lead = get_lead_with_phone_number(number)

	def after_insert(self):
		self.trigger_call_popup()

	def on_update(self):
		doc_before_save = self.get_doc_before_save()
		if not doc_before_save: return
		if doc_before_save.status in ['Ringing'] and self.status in ['Missed', 'Completed']:
			frappe.publish_realtime('call_{id}_disconnected'.format(id=self.id), self)
		elif doc_before_save.to != self.to:
			self.trigger_call_popup()

	def trigger_call_popup(self):
		scheduled_employees = get_scheduled_employees_for_popup(self.medium)
		employee_emails = get_employees_with_number(self.to)

		# check if employees with matched number are scheduled to receive popup
		emails = set(scheduled_employees).intersection(employee_emails)

		# # if no employee found with matching phone number then show popup to scheduled employees
		# emails = emails or scheduled_employees if employee_emails

		for email in emails:
			frappe.publish_realtime('show_call_popup', self, user=email)

@frappe.whitelist()
def add_call_summary(call_log, summary):
	doc = frappe.get_doc('Call Log', call_log)
	doc.add_comment('Comment', frappe.bold(_('Call Summary')) + '<br><br>' + summary)

def get_employees_with_number(number):
	number = strip_number(number)
	if not number: return []

	employee_emails = frappe.cache().hget('employees_with_number', number)
	if employee_emails: return employee_emails

	employees = frappe.get_all('Employee', filters={
		'cell_number': ['like', '%{}%'.format(number)],
		'user_id': ['!=', '']
	}, fields=['user_id'])

	employee_emails = [employee.user_id for employee in employees]
	frappe.cache().hset('employees_with_number', number, employee_emails)

	return employee_emails

def set_caller_information(doc, state):
	'''Called from hooks on creation of Lead or Contact'''
	if doc.doctype not in ['Lead', 'Contact']: return

	numbers = [doc.get('phone'), doc.get('mobile_no')]
	# contact for Contact and lead for Lead
	fieldname = doc.doctype.lower()

	# contact_name or lead_name
	display_name_field = '{}_name'.format(fieldname)

	# Contact now has all the nos saved in child table
	if doc.doctype == 'Contact':
		numbers = [d.phone for d in doc.phone_nos]

	for number in numbers:
		number = strip_number(number)
		if not number: continue

		filters = frappe._dict({
			'from': ['like', '%{}'.format(number)],
			fieldname: ''
		})

		logs = frappe.get_all('Call Log', filters=filters)

		for log in logs:
			frappe.db.set_value('Call Log', log.name, {
				fieldname: doc.name,
				display_name_field: doc.get_title()
			}, update_modified=False)
