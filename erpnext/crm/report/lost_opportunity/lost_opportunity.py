# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.query_builder import DocType
from frappe.query_builder.custom import GROUP_CONCAT
from frappe.query_builder.functions import Date

Opportunity = DocType("Opportunity")
OpportunityLostReasonDetail = DocType("Opportunity Lost Reason Detail")


def execute(filters=None):
	columns, data = get_columns(), get_data(filters)
	return columns, data


def get_columns():
	columns = [
		{
			"label": _("Opportunity"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Opportunity",
			"width": 170,
		},
		{
			"label": _("Opportunity From"),
			"fieldname": "opportunity_from",
			"fieldtype": "Link",
			"options": "DocType",
			"width": 130,
		},
		{
			"label": _("Party"),
			"fieldname": "party_name",
			"fieldtype": "Dynamic Link",
			"options": "opportunity_from",
			"width": 160,
		},
		{
			"label": _("Customer/Lead Name"),
			"fieldname": "customer_name",
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"label": _("Opportunity Type"),
			"fieldname": "opportunity_type",
			"fieldtype": "Data",
			"width": 130,
		},
		{"label": _("Lost Reasons"), "fieldname": "lost_reason", "fieldtype": "Data", "width": 220},
		{
			"label": _("Sales Stage"),
			"fieldname": "sales_stage",
			"fieldtype": "Link",
			"options": "Sales Stage",
			"width": 150,
		},
		{
			"label": _("Territory"),
			"fieldname": "territory",
			"fieldtype": "Link",
			"options": "Territory",
			"width": 150,
		},
	]
	return columns


def get_data(filters):
	query = (
		frappe.qb.from_(Opportunity)
		.left_join(OpportunityLostReasonDetail)
		.on(
			(OpportunityLostReasonDetail.parenttype == "Opportunity")
			& (OpportunityLostReasonDetail.parent == Opportunity.name)
		)
		.select(
			Opportunity.name,
			Opportunity.opportunity_from,
			Opportunity.party_name,
			Opportunity.customer_name,
			Opportunity.opportunity_type,
			GROUP_CONCAT(OpportunityLostReasonDetail.lost_reason, alias="lost_reason").separator(", "),
			Opportunity.sales_stage,
			Opportunity.territory,
		)
		.where(
			(Opportunity.status == "Lost")
			& (Opportunity.company == filters.get("company"))
			& (Date(Opportunity.modified).between(filters.get("from_date"), filters.get("to_date")))
		)
		.groupby(Opportunity.name)
		.orderby(Opportunity.creation)
	)

	query = get_conditions(filters, query)

	return query.run(as_dict=1)


def get_conditions(filters, query):
	if filters.get("territory"):
		query = query.where(Opportunity.territory == filters.get("territory"))

	if filters.get("opportunity_from"):
		query = query.where(Opportunity.opportunity_from == filters.get("opportunity_from"))

	if filters.get("party_name"):
		query = query.where(Opportunity.party_name == filters.get("party_name"))

	if filters.get("lost_reason"):
		query = query.where(OpportunityLostReasonDetail.lost_reason == filters.get("lost_reason"))

	return query
