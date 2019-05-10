# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe import _
import frappe
from erpnext.hr.doctype.daily_work_summary.daily_work_summary import get_user_emails_from_group

def execute(filters=None):
	if not filters.group: return [], []
	columns, data = get_columns(), get_data(filters)
	return columns, data

def get_columns(filters=None):
	columns = [
		{
			"label": _("User"),
			"fieldname": "user",
			"fieldtype": "Data",
			"width": 300
		},
		{
			"label": _("Replies"),
			"fieldname": "count",
			"fieldtype": "data",
			"width": 100,
			"align": 'right',
		},
		{
			"label": _("Total"),
			"fieldname": "total",
			"fieldtype": "data",
			"width": 100,
			"align": 'right',
		}
	]
	return columns

def get_data(filters):
	daily_summary_emails = frappe.get_all('Daily Work Summary',
		fields=["name"],
		filters=[["creation","Between", filters.range]])
	daily_summary_emails = [d.get('name') for d in daily_summary_emails]

	replies = frappe.db.sql("""
			select `tabCommunication`.content,
					`tabCommunication`.text_content,
					`tabCommunication`.sender
			from `tabCommunication`
				inner join `tabDynamic Link`
					on `tabCommunication`.name=`tabDynamic Link`.parent
			where `tabDynamic Link`.link_doctype = 'Daily Work Summary'
					and `tabDynamic Link`.link_name in %(daily_summary_emails)s
					and `tabCommunication`.communication_type='Communication'
					and `tabCommunication`.sent_or_received='Received'
			order by `tabCommunication`.creation asc
		""",{
				"daily_summary_emails": daily_summary_emails
			}, as_dict=True, debug=True)

	data = []
	total = len(daily_summary_emails)
	for user in get_user_emails_from_group(filters.group):
		user_name = frappe.get_value('User', user, 'full_name')
		count = len([d for d in replies if d.sender == user])
		data.append([user_name, count, total])
	return data