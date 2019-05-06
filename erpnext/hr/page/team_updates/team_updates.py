from __future__ import unicode_literals

import frappe
from email_reply_parser import EmailReplyParser

@frappe.whitelist()
def get_data(start=0):
	#frappe.only_for('Employee', 'System Manager')
	limit = 40
	replies = frappe.db.sql("""
			select `tabCommunication`.content, `tabCommunication`.text_content, `tabCommunication`.sender, `tabCommunication`.creation
			from `tabCommunication`
			inner join `tabDynamic Link`
			on `tabCommunication`.name=`tabDynamic Link`.parent where
			`tabDynamic Link`.link_doctype='Daily Work Summary'
			order by `tabCommunication`.creation desc
			limit %(start)s, %(limit)s
		""",
		{
			"start": start,
			"limit": limit,
		}, as_dict=True)

	for d in replies:
		d.sender_name = frappe.db.get_value("Employee", {"user_id": d.sender},
			"employee_name") or d.sender
		if d.text_content:
			d.content = frappe.utils.md_to_html(EmailReplyParser.parse_reply(d.text_content))

	return data