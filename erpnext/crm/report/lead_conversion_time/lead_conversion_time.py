# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _, msgprint
from frappe.query_builder.functions import Count, Date
from frappe.utils import date_diff, flt, parse_addr, split_emails


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
	communication_list = []
	converted_leads = set()
	for opportunity in get_lead_opportunities():
		if opportunity.party_name in converted_leads:
			continue
		row = get_conversion_details(opportunity, filters)
		if row:
			converted_leads.add(opportunity.party_name)
			communication_list.append(row)
	return communication_list


def get_lead_opportunities() -> list[dict]:
	return frappe.get_list(
		"Opportunity",
		filters={"opportunity_from": "Lead"},
		fields=["party_name", "customer_name", "contact_email"],
		order_by="creation",
	)


def get_conversion_details(d: dict, filters: dict) -> dict | None:
	si = frappe.qb.DocType("Sales Invoice")
	comm = frappe.qb.DocType("Communication")

	invoice = (
		frappe.qb.from_(si)
		.select(si.posting_date)
		.where(
			(si.contact_email == d.contact_email)
			& si.posting_date.between(filters.from_date, filters.to_date)
			& (si.docstatus == 1)
		)
		.orderby(si.posting_date)
		.limit(1)
		.run()
	)

	if not invoice:
		return

	invoice_date = invoice[0][0]

	communication_count = (
		frappe.qb.from_(comm)
		.select(Count("*"))
		.where((comm.sender == d.contact_email) & (Date(comm.communication_date) <= invoice_date))
		.run()
	)[0][0]

	if not communication_count:
		return

	first_contact = get_first_contact_date(d.contact_email)
	if not first_contact:
		return

	return {
		"customer": d.customer_name,
		"interactions": communication_count,
		"duration": flt(date_diff(invoice_date, first_contact)),
		"support_tickets": len(frappe.db.get_all("Issue", {"raised_by": d.contact_email})),
	}


def get_first_contact_date(email: str):
	comm = frappe.qb.DocType("Communication")
	communications = (
		frappe.qb.from_(comm)
		.select(comm.recipients, Date(comm.communication_date))
		.where(comm.recipients.like(f"%{email}%") & comm.communication_date.isnotnull())
		.orderby(comm.communication_date)
		.run()
	)
	for recipients, communication_date in communications:
		if is_recipient(email, recipients):
			return communication_date


def is_recipient(email: str, recipients: str) -> bool:
	return any(parse_addr(recipient)[1].lower() == email.lower() for recipient in split_emails(recipients))
