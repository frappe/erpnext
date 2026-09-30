# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _, msgprint
from frappe.query_builder.functions import Count, Date
from frappe.utils import date_diff, flt


def execute(filters=None):
	if not filters:
		filters = {}

	communication_list = get_communication_details(filters)
	columns = get_columns()

	if not communication_list:
		msgprint(_("No record found"))
		return columns, communication_list

	data = []
	for communication in communication_list:
		row = [
			communication.get("customer"),
			communication.get("interactions"),
			communication.get("duration"),
			communication.get("support_tickets"),
		]
		data.append(row)

	# add the average row
	total_interactions = 0
	total_duration = 0
	total_tickets = 0

	for row in data:
		total_interactions += row[1]
		total_duration += row[2]
		total_tickets += row[3]
	data.append(
		[
			"Average",
			total_interactions / len(data),
			total_duration / len(data),
			total_tickets / len(data),
		]
	)
	return columns, data


def get_columns():
	return [
		{
			"label": _("Customer"),
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 120,
		},
		{
			"label": _("No of Interactions"),
			"fieldname": "interactions",
			"fieldtype": "Float",
			"width": 120,
		},
		{"label": _("Duration in Days"), "fieldname": "duration", "fieldtype": "Float", "width": 120},
		{
			"label": _("Support Tickets"),
			"fieldname": "support_tickets",
			"fieldtype": "Float",
			"width": 120,
		},
	]


def get_communication_details(filters):
	communication_count = None
	communication_list = []
	opportunities = frappe.db.get_values(
		"Opportunity",
		{"opportunity_from": "Lead"},
		["name", "customer_name", "contact_email"],
		as_dict=1,
	)

	si = frappe.qb.DocType("Sales Invoice")
	comm = frappe.qb.DocType("Communication")

	for d in opportunities:
		invoice = (
			frappe.qb.from_(si)
			.select(Date(si.creation))
			.where(
				(si.contact_email == d.contact_email)
				& Date(si.creation).between(filters.from_date, filters.to_date)
				& (si.docstatus != 2)
			)
			.orderby(si.creation)
			.limit(1)
			.run()
		)

		if not invoice:
			continue

		invoice_date = invoice[0][0]

		communication_count = (
			frappe.qb.from_(comm)
			.select(Count("*"))
			.where((comm.sender == d.contact_email) & (Date(comm.communication_date) <= invoice_date))
			.run()
		)[0][0]

		if not communication_count:
			continue

		first_contact = (
			frappe.qb.from_(comm)
			.select(Date(comm.communication_date))
			.where((comm.recipients == d.contact_email) & comm.communication_date.isnotnull())
			.orderby(comm.communication_date)
			.limit(1)
			.run()
		)
		first_contact = first_contact[0][0] if first_contact else None
		if not first_contact:
			continue

		duration = flt(date_diff(invoice_date, first_contact))

		support_tickets = len(frappe.db.get_all("Issue", {"raised_by": d.contact_email}))
		communication_list.append(
			{
				"customer": d.customer_name,
				"interactions": communication_count,
				"duration": duration,
				"support_tickets": support_tickets,
			}
		)
	return communication_list
