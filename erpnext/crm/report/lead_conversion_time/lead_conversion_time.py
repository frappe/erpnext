# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, msgprint
from frappe.utils import date_diff, flt

def execute(filters=None):
	if not filters: filters = {}

	communication_list = get_communication_details(filters)
	columns = get_columns()

	if not communication_list:
		msgprint(_("No record found"))
		return columns, communication_list

	data = []
	for communication in communication_list:
		row = [communication.get('customer'), communication.get('interactions'),\
			communication.get('duration'), communication.get('support_tickets')]
		data.append(row)

	# add the average row
	total_interactions = 0
	total_duration = 0
	total_tickets = 0

	for row in data:
		total_interactions += row[1]
		total_duration += row[2]
		total_tickets += row[3]
	data.append(['Average', total_interactions/len(data), total_duration/len(data), total_tickets/len(data)])
	return columns, data

def get_columns():
	return [
		{
			"label": _("Customer"),
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 120
		},
		{
			"label": _("No of Interactions"),
			"fieldname": "interactions",
			"fieldtype": "Float",
			"width": 120
		},
		{
			"label": _("Duration in Days"),
			"fieldname": "duration",
			"fieldtype": "Float",
			"width": 120
		},
		{
			"label": _("Support Tickets"),
			"fieldname": "support_tickets",
			"fieldtype": "Float",
			"width": 120
		}
	]

def get_communication_details(filters):
	communication_count = None
	communication_list = []
	opportunities = frappe.db.get_values('Opportunity', {'enquiry_from': 'Lead'},\
		['name', 'customer_name', 'lead', 'contact_email'], as_dict=1)

	for d in opportunities:
		invoice = frappe.db.sql('''
				SELECT
					date(creation)
				FROM
					`tabSales Invoice`
				WHERE
					contact_email = %s AND date(creation) between %s and %s AND docstatus != 2
				ORDER BY
					creation
				LIMIT 1
			''', (d.contact_email, filters.from_date, filters.to_date))

		if not invoice: continue

		communication_count = frappe.db.sql('''
				SELECT
					count(*)
				FROM
					`tabCommunication`
				WHERE
					sender = %s AND date(communication_date) <= %s
			''', (d.contact_email, invoice))[0][0]

		if not communication_count: continue

		first_contact = frappe.db.sql('''
				SELECT
					date(communication_date)
				FROM
					`tabCommunication`
				WHERE
					recipients  = %s
				ORDER BY
					communication_date
				LIMIT 1
			''', (d.contact_email))[0][0]

		duration = flt(date_diff(invoice[0][0], first_contact))

		support_tickets = len(frappe.db.get_all('Issue', {'raised_by': d.contact_email}))
		communication_list.append({'customer': d.customer_name, 'interactions': communication_count, 'duration': duration, 'support_tickets': support_tickets})
	return communication_list
