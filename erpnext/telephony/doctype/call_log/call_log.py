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

from erpnext.crm.doctype.lead.lead import get_lead_with_phone_number

END_CALL_STATUSES = ['No Answer', 'Completed', 'Busy', 'Failed']
ONGOING_CALL_STATUSES = ['Ringing', 'In Progress']


class CallLog(Document):
	def validate(self):
		deduplicate_dynamic_links(self)

	def before_insert(self):
		"""Add lead(third party person) links to the document.
		"""
		lead_number = self.get('from') if self.is_incoming_call() else self.get('to')
		lead_number = strip_number(lead_number)

		contact = get_contact_with_phone_number(strip_number(lead_number))
		if contact:
			self.add_link(link_type='Contact', link_name=contact)

		lead = get_lead_with_phone_number(lead_number)
		if lead:
			self.add_link(link_type='Lead', link_name=lead)

	def after_insert(self):
		self.trigger_call_popup()

	def on_update(self):
		def _is_call_missed(doc_before_save, doc_after_save):
			# FIXME: This works for Exotel but not for all telepony providers
			return doc_before_save.to != doc_after_save.to and doc_after_save.status not in END_CALL_STATUSES

		def _is_call_ended(doc_before_save, doc_after_save):
			return doc_before_save.status not in END_CALL_STATUSES and self.status in END_CALL_STATUSES

		doc_before_save = self.get_doc_before_save()
		if not doc_before_save: return

		if _is_call_missed(doc_before_save, self):
			frappe.publish_realtime('call_{id}_missed'.format(id=self.id), self)
			self.trigger_call_popup()

		if _is_call_ended(doc_before_save, self):
			frappe.publish_realtime('call_{id}_ended'.format(id=self.id), self)

	def is_incoming_call(self):
		return self.type == 'Incoming'

	def add_link(self, link_type, link_name):
		self.append('links', {
			'link_doctype': link_type,
			'link_name': link_name
		})

	def trigger_call_popup(self):
		if self.is_incoming_call():
			scheduled_employees = get_scheduled_employees_for_popup(self.medium)
			employee_emails = get_employees_with_number(self.to)

			# check if employees with matched number are scheduled to receive popup
			emails = set(scheduled_employees).intersection(employee_emails)

			if frappe.conf.developer_mode:
				self.add_comment(text=f"""
					Scheduled Employees: {scheduled_employees}
					Matching Employee: {employee_emails}
					Show Popup To: {emails}
				""")

			if employee_emails and not emails:
				self.add_comment(text=_("No employee was scheduled for call popup"))

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

def link_existing_conversations(doc, state):
	"""
	Called from hooks on creation of Contact or Lead to link all the existing conversations.
	"""
	if doc.doctype != 'Contact': return
	try:
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
						WHEN dl.link_doctype = %(doctype)s AND dl.link_name = %(docname)s
						THEN 1
						ELSE 0
					END
				)=0
			""", dict(
				phone_number='%{}'.format(number),
				docname=doc.name,
				doctype = doc.doctype
				)
			)

			for log in logs:
				call_log = frappe.get_doc('Call Log', log)
				call_log.add_link(link_type=doc.doctype, link_name=doc.name)
				call_log.save()
			frappe.db.commit()
	except Exception:
		frappe.log_error(title=_('Error during caller information update'))

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
			'icon': 'call',
			'is_card': True,
			'creation': log.creation,
			'template': 'call_link',
			'template_data': log
		})

	return timeline_contents

