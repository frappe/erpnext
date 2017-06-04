# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from email_reply_parser import EmailReplyParser
from erpnext.hr.doctype.employee.employee import is_holiday
from frappe.utils import formatdate
from markdown2 import markdown

class DailyWorkSummary(Document):
	def send_mails(self, settings, emails):
		'''Send emails to get daily work summary to all employees'''
		incoming_email_account = frappe.db.get_value('Email Account',
			dict(enable_incoming=1, default_incoming=1), 'email_id')

		self.db_set('email_sent_to', '\n'.join(emails))
		frappe.sendmail(recipients = emails, message = settings.message,
			subject = settings.subject, reference_doctype=self.doctype,
			reference_name=self.name, reply_to = incoming_email_account)

	def send_summary(self):
		'''Send summary of all replies. Called at midnight'''
		message = self.get_summary_message()

		frappe.sendmail(recipients = get_employee_emails(self.company, False),
			message = message,
			subject = _('Daily Work Summary for {0}').format(self.company),
			reference_doctype=self.doctype, reference_name=self.name)

		self.db_set('status', 'Sent')

	def get_summary_message(self):
		'''Return summary of replies as HTML'''
		settings = frappe.get_doc('Daily Work Summary Settings')

		replies = frappe.get_all('Communication', fields=['content', 'text_content', 'sender'],
			filters=dict(reference_doctype=self.doctype, reference_name=self.name,
				communication_type='Communication', sent_or_received='Received'),
				order_by='creation asc')

		did_not_reply = self.email_sent_to.split()

		for d in replies:
			d.sender_name = frappe.db.get_value("Employee", {"user_id": d.sender},
				"employee_name") or d.sender
			if d.sender in did_not_reply:
				did_not_reply.remove(d.sender)
			if d.text_content:
				d.content = markdown(EmailReplyParser.parse_reply(d.text_content))


		did_not_reply = [(frappe.db.get_value("Employee", {"user_id": email}, "employee_name") or email)
			for email in did_not_reply]

		return frappe.render_template(self.get_summary_template(),
			dict(replies=replies,
				original_message=settings.message,
				title=_('Daily Work Summary for {0}'.format(formatdate(self.creation))),
				did_not_reply= ', '.join(did_not_reply) or '',
				did_not_reply_title = _('No replies from')))

	def get_summary_template(self):
		return '''
<h3>{{ title }}</h3>

{% for reply in replies %}
<h4>{{ reply.sender_name }}</h4>
<p style="padding-bottom: 20px">
	{{ reply.content }}
</p>
<hr>
{% endfor %}

{% if did_not_reply %}
<p>{{ did_not_reply_title }}: {{ did_not_reply }}</p>
{% endif %}

'''

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
				continue
			out.append(e.user_id)

	return out


