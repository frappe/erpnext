# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from erpnext.crm.doctype.utils import get_scheduled_employees_for_popup, strip_number
from frappe.contacts.doctype.contact.contact import get_contact_with_phone_number
from frappe.core.doctype.dynamic_link.dynamic_link import deduplicate_dynamic_links

END_CALL_STATUSES = ['No Answer', 'Completed', 'Busy', 'Failed']
ONGOING_CALL_STATUSES = ['Ringing', 'In Progress']

class CallLog(Document):
	def validate(self):
		deduplicate_dynamic_links(self)

	def before_insert(self):
		self.set_caller_information()

	def after_insert(self):
		if self.get('type') == 'Incoming':
			self.trigger_call_popup()

	def on_update(self):
		if self.get('type') == 'Incoming':
			doc_before_save = self.get_doc_before_save()
			if not doc_before_save: return
			if doc_before_save.status in ONGOING_CALL_STATUSES and self.status in END_CALL_STATUSES:
				frappe.publish_realtime('call_{id}_ended'.format(id=self.id), self)
			elif doc_before_save.to != self.to:
				self.trigger_call_popup()

	def set_caller_information(self):
		number = self.get('from') if self.type == 'Incoming' else self.get('to')
		number = strip_number(number)
		contact = get_contact_with_phone_number(number)
		if contact:
			self.link_contact(contact)

	def link_contact(self, contact):
		self.append('links', {
			'link_doctype': 'Contact',
			'link_name': contact
		})

	def trigger_call_popup(self):
		scheduled_employees = get_scheduled_employees_for_popup(self.medium)
		employee_emails = get_employees_with_number(self.to)

		# check if employees with matched number are scheduled to receive popup
		emails = set(scheduled_employees).intersection(employee_emails)

		if employee_emails and not emails:
			self.add_comment(text=_("No employee was scheduled for call popup"))

		for email in emails:
			frappe.publish_realtime('show_call_popup', self, user=email)


@frappe.whitelist()
def add_call_summary(call_log, summary):
	doc = frappe.get_doc('Call Log', call_log)
	doc.summary = summary
	doc.save()

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
	'''Called from hooks on creation of Contact'''
	if doc.doctype != 'Contact': return

	numbers = [d.phone for d in doc.phone_nos]

	for number in numbers:
		number = strip_number(number)
		if not number: continue
		logs = frappe.db.sql_list("""
			SELECT cl.name FROM `tabCall Log` cl
			LEFT JOIN `tabDynamic Link` dl
			ON cl.name = dl.parent
			WHERE (cl.`from` like %(phone_number)s or cl.`to` like %(phone_number)s)
			GROUP BY cl.name
			HAVING SUM(
				CASE
					WHEN dl.link_doctype = 'Contact' AND dl.link_name = %(contact_name)s
					THEN 1
					ELSE 0
				END
			)=0
		""", dict(phone_number='%{}'.format(number),
			contact_name=doc.name))

		for log in logs:
			call_log = frappe.get_doc('Call Log', log)
			call_log.link_contact(doc.name)
			call_log.save()

def get_linked_call_logs(doctype, docname):
	# content will be shown in timeline
	logs = frappe.get_all('Dynamic Link', fields=['parent'], filters={
		'parenttype': 'Call Log',
		'link_doctype': doctype,
		'link_name': docname
	})

	logs = set([log.parent for log in logs])

	logs = frappe.get_all('Call Log', fields=['*'], filters={
		'name': ['in', logs]
	})

	timeline_contents = []
	for log in logs:
		log.show_call_button = 0
		timeline_contents.append({
			'creation': log.creation,
			'template': 'call_link',
			'template_data': log
		})

	return timeline_contents

@frappe.whitelist()
def get_caller_activities(number):
	activities = {
		'issues': []
	}
	number = strip_number(number)
	contact = get_contact_with_phone_number(number)

	if not contact:
		return activities

	contact_doc = frappe.get_doc('Contact', contact)

	for link in contact_doc.links:
		if link.link_doctype == 'Customer':
			activities['issues'].extend(get_issues_by_customer(link.link_name))
		if link.link_doctype == 'Lead':
			activities['issues'].extend(get_issues_by_lead(link.link_name))

	return activities

def get_issues_by_customer(customer):
	issues = frappe.get_all('Issue', {
		'customer': customer
	})
	return issues

def get_issues_by_lead(lead):
	issues = frappe.get_all('Issue', {
		'lead': lead
	})
	return issues

@frappe.whitelist()
def link_issue(call_id, issue):
	doc = frappe.get_doc('Call Log', call_id)

	doc.append('links', {
		'link_doctype': 'Issue',
		'link_name': issue
	})

	doc.save(ignore_permissions=True)
