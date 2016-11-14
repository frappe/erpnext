# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from email_reply_parser import EmailReplyParser
from erpnext.hr.doctype.employee.employee import is_holiday

class DailyWorkSummary(Document):
	def send_mails(self, settings, emails):
		'''Send emails to get daily work summary to all employees'''
		incoming_email_account = frappe.db.get_value('Email Account',
			dict(enable_incoming=1, default_incoming=1), 'email_id')
		frappe.sendmail(recipients = emails, message = settings.message,
			subject = settings.subject, reference_doctype=self.doctype,
			reference_name=self.name, reply_to = incoming_email_account)

	def send_summary(self):
		'''Send summary of all replies'''
		message = self.get_summary_message()

		frappe.sendmail(recipients = get_employee_emails(self.company, False), message = message,
			subject = _('Daily Work Summary for {0}').format(self.company),
			reference_doctype=self.doctype, reference_name=self.name)

	def get_summary_message(self):
		'''Return summary of replies as HTML'''
		settings = frappe.get_doc('Daily Work Summary Settings')

		replies = frappe.get_all('Communication', fields=['content', 'text_content', 'sender'],
			filters=dict(reference_doctype=self.doctype, reference_name=self.name,
				communication_type='Communication', sent_or_received='Received'))

		if not replies:
			return None

		for d in replies:
			if d.text_content:
				d.content = EmailReplyParser.parse_reply(d.text_content)

		return frappe.render_template(template, dict(replies=replies,
			original_message=settings.message))

def get_employee_emails(company, only_working=True):
	'''Returns list of Employee user ids for the given company who are working today

	:param company: Company `name`'''
	employee_list = frappe.get_all('Employee', fields=['name', 'user_id'],
		filters={'status': 'Active', 'company': company})

	out = []
	for e in employee_list:
		if e.user_id:
			if only_working and is_holiday(e.name):
				# don't add if holiday
				pass
			out.append(e.user_id)

	return out


template = '''
<p>Summary of replies:</p>

{% for reply in replies %}
<h5>{{ frappe.db.get_value("Employee", {"user_id": reply.sender}, "employee_name") or reply.sender }}<h5>
<div style="padding-bottom: 20px">
	{{ reply.content }}
</div>
{% endfor %}
'''