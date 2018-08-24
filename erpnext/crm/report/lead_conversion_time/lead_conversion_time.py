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
			communication.get('duration'), communication.get('average')]
		data.append(row)

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
			"fieldtype": "Int",
			"width": 120
		},
		{
			"label": _("Duration in Days"),
			"fieldname": "duration",
			"fieldtype": "Int",
			"width": 120
		},
		{
			"label": _("Average"),
			"fieldname": "average",
			"fieldtype": "Float",
			"width": 120
		}
	]

def get_communication_details(filters):
	communication_count = None
	communication_list = []
	opportunies = frappe.db.get_values('Opportunity', {'enquiry_from': 'Lead'},\
		['name', 'customer_name', 'lead', 'contact_email'], as_dict=1)

	for d in opportunies:
		invoice = frappe.db.sql('''
				SELECT
					date(creation)
				FROM
					`tabSales Invoice`
				WHERE
					contact_email = %s AND date(creation) between %s and %s
				ORDER BY
					creation
				LIMIT 1
			''', (d.contact_email, filters.from_date, filters.to_date))

		if not invoice: continue

		communication_count = len(frappe.db.get_all('Communication', {'reference_name': d.name, 'communication_type': 'Communication'})) +\
			len(frappe.db.get_all('Communication', {'reference_name': d.lead, 'communication_type': 'Communication'}))

		if not communication_count: continue

		first_contact = frappe.db.sql('''
				SELECT
					date(communication_date)
				FROM
					`tabCommunication`
				WHERE
					reference_name = %s AND recipients  = %s
				ORDER BY
					communication_date
				LIMIT 1
			''', (d.lead, d.contact_email))

		duration = flt(date_diff(invoice[0][0], first_contact[0][0]))
		average_time = flt((communication_count + duration) / 2)

		communication_list.append({'customer': d.customer_name, 'interactions': communication_count, 'duration': duration, 'average': average_time})
	return communication_list
