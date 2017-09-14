# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from email_reply_parser import EmailReplyParser
from erpnext.hr.doctype.employee.employee import is_holiday
from frappe.utils import global_date_format
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
		args = self.get_message_details()

		frappe.sendmail(recipients = get_employee_emails(self.company, False),
			template='daily_work_summary',
			args=args,
			subject = _('Daily Work Summary for {0}').format(self.company),
			reference_doctype=self.doctype, reference_name=self.name)

		self.db_set('status', 'Sent')

	def get_message_details(self):
		'''Return args for template'''
		settings = frappe.get_doc('Daily Work Summary Settings')

		replies = frappe.get_all('Communication', fields=['content', 'text_content', 'sender'],
			filters=dict(reference_doctype=self.doctype, reference_name=self.name,
				communication_type='Communication', sent_or_received='Received'),
				order_by='creation asc')

		did_not_reply = self.email_sent_to.split()

		for d in replies:
			emp = frappe.db.get_values("Employee", {"user_id": d.sender},
				["employee_name", "image"], as_dict=True)

			d.sender_name = emp[0].employee_name if emp else d.sender
			d.image = emp[0].image if emp and emp[0].image else None
			
			original_image = d.image
			# make thumbnail image
			try:
				if original_image:
					file_name = frappe.get_list('File', {'file_url': original_image})

					if file_name:
						file_name = file_name[0].name
						file_doc = frappe.get_doc('File', file_name)
						thumbnail_image = file_doc.make_thumbnail(
							set_as_thumbnail=False,
							width=100,
							height=100,
							crop=True
						)
						d.image = thumbnail_image
			except:
				d.image = original_image

			if d.sender in did_not_reply:
				did_not_reply.remove(d.sender)
			if d.text_content:
				d.content = markdown(EmailReplyParser.parse_reply(d.text_content))


		did_not_reply = [(frappe.db.get_value("Employee", {"user_id": email}, "employee_name") or email)
			for email in did_not_reply]

		return dict(replies=replies,
			original_message=settings.message,
			title=_('Daily Work Summary for {0}'.format(global_date_format(self.creation))),
			did_not_reply= ', '.join(did_not_reply) or '',
			did_not_reply_title = _('No replies from'))


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


