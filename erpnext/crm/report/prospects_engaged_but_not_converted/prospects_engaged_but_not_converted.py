# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.query_builder import Criterion, Order
from frappe.utils import add_days, cint, now


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
			"options": "DocType",
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


REFERENCE_DOCTYPES = (
	("Opportunity", "party_name", {"opportunity_from": "Lead"}),
	("Quotation", "party_name", {"quotation_to": "Lead"}),
	("Issue", "lead", {"status": ["!=", "Closed"]}),
)


def get_data(filters):
	lead_details = []
	leads = frappe.get_list(
		"Lead", fields=["name", "lead_name", "company_name"], filters=get_lead_filters(filters)
	)
	if not leads:
		return lead_details

	references = get_references([lead.name for lead in leads])
	limit = cint(filters.get("no_of_interaction"))
	for lead in leads:
		for communication in get_received_communications(references[lead.name], limit):
			lead_details.append([lead.name, lead.lead_name, lead.company_name, *communication])

	return lead_details


def get_references(lead_names: list) -> dict:
	"""Map each lead to the names, per DocType, of itself and the documents linked to it that the user can read."""
	references = {name: {"Lead": {name}} for name in lead_names}
	for doctype, lead_field, filters in REFERENCE_DOCTYPES:
		filters = {**filters, lead_field: ["in", lead_names]}
		for row in get_readable(doctype, filters, ["name", lead_field]):
			references[row[lead_field]].setdefault(doctype, set()).add(row.name)
	return references


def get_received_communications(references: dict, limit: int) -> list:
	communication = frappe.qb.DocType("Communication")
	# names are unique only within a DocType, so each DocType is matched with its own names
	matches = [
		(communication.reference_doctype == doctype) & communication.reference_name.isin(list(names))
		for doctype, names in references.items()
	]
	return (
		frappe.qb.from_(communication)
		.select(
			communication.reference_doctype,
			communication.reference_name,
			communication.content,
			communication.communication_date,
		)
		.where(Criterion.any(matches) & (communication.sent_or_received == "Received"))
		.orderby(communication.creation, order=Order.desc)
		.limit(limit)
		.run()
	)


def get_readable(doctype: str, filters: dict, fields: list) -> list:
	if not frappe.has_permission(doctype, "read"):
		return []
	return frappe.get_list(doctype, filters=filters, fields=fields)


def get_lead_filters(filters):
	lead_creation_date = get_creation_date_based_on_lead_age(filters)
	lead_filters = [["status", "!=", "Converted"], ["creation", "<=", lead_creation_date]]

	if filters.get("lead"):
		lead_filters.append(["name", "=", filters.get("lead")])
	return lead_filters


def get_creation_date_based_on_lead_age(filters):
	return add_days(now(), (filters.get("lead_age") * -1))
