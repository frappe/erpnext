# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import add_days, now


def execute(filters=None):
	columns, data = [], []
	set_defaut_value_for_filters(filters)
	columns = get_columns()
	data = get_data(filters)

	return columns, data


def set_defaut_value_for_filters(filters):
	if not filters.get("no_of_interaction"):
		filters["no_of_interaction"] = 1
	if not filters.get("lead_age"):
		filters["lead_age"] = 60


def get_columns():
	columns = [
		{"label": _("Lead"), "fieldname": "lead", "fieldtype": "Link", "options": "Lead", "width": 130},
		{"label": _("Name"), "fieldname": "name", "width": 120},
		{"label": _("Organization"), "fieldname": "organization", "width": 120},
		{
			"label": _("Reference Document Type"),
			"fieldname": "reference_document_type",
			"fieldtype": "Link",
			"options": "Doctype",
			"width": 100,
		},
		{
			"label": _("Reference Name"),
			"fieldname": "reference_name",
			"fieldtype": "Dynamic Link",
			"options": "reference_document_type",
			"width": 140,
		},
		{
			"label": _("Last Communication"),
			"fieldname": "last_communication",
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"label": _("Last Communication Date"),
			"fieldname": "last_communication_date",
			"fieldtype": "Date",
			"width": 100,
		},
	]
	return columns


def get_data(filters):
	lead_details = []
	lead_filters = get_lead_filters(filters)
	leads = frappe.get_all("Lead", fields=["name", "lead_name", "company_name"], filters=lead_filters)
	if not leads:
		return lead_details

	lead_names = [lead.name for lead in leads]

	# Collect the documents (and the lead itself) that communications may reference, for all leads in
	# three bulk queries instead of three per lead.
	reference_names = {name: {name} for name in lead_names}
	for opp in frappe.get_all(
		"Opportunity",
		filters={"opportunity_from": "Lead", "party_name": ["in", lead_names]},
		fields=["name", "party_name"],
	):
		reference_names[opp.party_name].add(opp.name)
	for quotation in frappe.get_all(
		"Quotation",
		filters={"quotation_to": "Lead", "party_name": ["in", lead_names]},
		fields=["name", "party_name"],
	):
		reference_names[quotation.party_name].add(quotation.name)
	for issue in frappe.get_all(
		"Issue",
		filters={"lead": ["in", lead_names], "status": ["!=", "Closed"]},
		fields=["name", "lead"],
	):
		reference_names[issue.lead].add(issue.name)

	for lead in leads:
		data = frappe.get_all(
			"Communication",
			filters={
				# constrain the doctype too: names are unique only within a doctype
				"reference_doctype": ["in", ["Lead", "Opportunity", "Quotation", "Issue"]],
				"reference_name": ["in", list(reference_names[lead.name])],
				"sent_or_received": "Received",
			},
			fields=["reference_doctype", "reference_name", "content", "communication_date"],
			order_by="creation desc",
			limit=filters.get("no_of_interaction"),
			as_list=True,
		)

		for lead_info in data:
			lead_data = [lead.name, lead.lead_name, lead.company_name, *list(lead_info)]
			lead_details.append(lead_data)

	return lead_details


def get_lead_filters(filters):
	lead_creation_date = get_creation_date_based_on_lead_age(filters)
	lead_filters = [["status", "!=", "Converted"], ["creation", ">", lead_creation_date]]

	if filters.get("lead"):
		lead_filters.append(["name", "=", filters.get("lead")])
	return lead_filters


def get_creation_date_based_on_lead_age(filters):
	return add_days(now(), (filters.get("lead_age") * -1))
