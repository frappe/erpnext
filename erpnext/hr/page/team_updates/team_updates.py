from __future__ import unicode_literals

import frappe
from email_reply_parser import EmailReplyParser

@frappe.whitelist()
def get_data(start=0):
	#frappe.only_for('Employee', 'System Manager')
	data = frappe.get_all('Communication',
		fields=('content', 'text_content', 'sender', 'creation'),
		filters=dict(reference_doctype='Daily Work Summary'),
		order_by='creation desc', limit=40, start=start)

	for d in data:
		d.sender_name = frappe.db.get_value("Employee", {"user_id": d.sender},
			"employee_name") or d.sender
		if d.text_content:
			d.content = frappe.utils.md_to_html(EmailReplyParser.parse_reply(d.text_content))

	return data