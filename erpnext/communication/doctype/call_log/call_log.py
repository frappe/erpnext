# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from erpnext.crm.doctype.utils import get_employee_emails_for_popup
from frappe.contacts.doctype.contact.contact import get_contact_with_phone_number
from erpnext.crm.doctype.lead.lead import get_lead_with_phone_number

class CallLog(Document):
	def before_insert(self):
		number = self.get('from').lstrip('0')
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
		employee_emails = get_employee_emails(self.to)
		for email in employee_emails:
			frappe.publish_realtime('show_call_popup', self, user=email)

@frappe.whitelist()
def add_call_summary(call_log, summary):
	doc = frappe.get_doc('Call Log', call_log)
	doc.add_comment('Comment', frappe.bold(_('Call Summary')) + '<br><br>' + summary)

def get_employee_emails(number):
	'''Returns employee's emails of employees that have passed phone number'''
	if not number: return

	employee_emails = frappe.cache().hget('employees_with_number', number)
	if employee_emails: return employee_emails

	employees = frappe.get_all('Employee', filters={
		'cell_number': ['like', '%{}'.format(number.lstrip('0'))],
		'user_id': ['!=', '']
	}, fields=['user_id'])

	employee_emails = [employee.user_id for employee in employees]
	frappe.cache().hset('employees_with_number', number, employee_emails)

	return employee