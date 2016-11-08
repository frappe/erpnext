# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class DailyWorkSummary(Document):
	def send_mails(self, settings):
		'''Send emails to get daily work summary to all employees'''
		frappe.sendmail(recipients = self.get_employee_emails(), message = settings.message,
			subject = settings.subject, reference_doctype=self.doctype, reference_name=self.name)

	def send_summary(self):
		'''Send summary of all replies'''
		settings = frappe.get_doc('Daily Work Summary Settings')

		replies = frappe.get_doc('Communication', fields=['content', 'sender'],
			filters=dict(reference_doctype=self.doctype, reference_name=self.name,
				communication_type='Email', sent_or_received='Received'))

		message = frappe.render_template(template, dict(replies=replies,
			original_message=settings.message))

		frappe.sendmail(recipients = self.get_employee_emails(), message = message,
			subject = _('Daily Work Summary for {0}').format(self.company),
			reference_doctype=self.doctype, reference_name=self.name)

	def get_employee_emails(self):
		return filter(None, [d.user_id for d in
			frappe.get_all('Employee', fields=['user_id'],
			filters={'status': 'Active', 'company': self.company})])

template = '''
<p>Summary of replies:</p>

{% for reply in replies %}
<h5>{{ frappe.db.get_value("Employee", reply.sender, "full_name") }}<h5>
<div style="padding-bottom: 20px">
	{{ reply.content.split(original_message)[0].strip() }}
</div>
{% endfor %}
'''