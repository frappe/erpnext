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

	for lead in frappe.get_all("Lead", fields=["name", "lead_name", "company_name"], filters=lead_filters):
		# Documents (and the lead itself) that communications may be referenced against
		reference_names = set()
		reference_names.update(
			frappe.get_all(
				"Opportunity",
				filters={"opportunity_from": "Lead", "party_name": lead.name},
				pluck="name",
			)
		)
		reference_names.update(
			frappe.get_all(
				"Quotation",
				filters={"quotation_to": "Lead", "party_name": lead.name},
				pluck="name",
			)
		)
		reference_names.update(
			frappe.get_all(
				"Issue",
				filters={"lead": lead.name, "status": ["!=", "Closed"]},
				pluck="name",
			)
		)
		reference_names.add(lead.name)

		data = frappe.get_all(
			"Communication",
			filters={
				"reference_name": ["in", list(reference_names)],
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
