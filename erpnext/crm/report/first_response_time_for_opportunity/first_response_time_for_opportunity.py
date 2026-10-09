# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.query_builder.functions import Avg, Date
from pypika import Order


def execute(filters=None):
	columns = [
		{"fieldname": "creation_date", "label": _("Date"), "fieldtype": "Date", "width": 300},
		{
			"fieldname": "first_response_time",
			"fieldtype": "Duration",
			"label": "First Response Time",
			"width": 300,
		},
	]

	opportunity = frappe.qb.DocType("Opportunity")
	creation_date = Date(opportunity.creation)
	data = (
		frappe.qb.from_(opportunity)
		.select(
			creation_date.as_("creation_date"), Avg(opportunity.first_response_time).as_("avg_response_time")
		)
		.where(
			creation_date.between(filters.from_date, filters.to_date) & (opportunity.first_response_time > 0)
		)
		.where(opportunity.name.isin(get_permitted_opportunities(filters)))
		.groupby(creation_date)
		.orderby(creation_date, order=Order.desc)
		.run()
	)

	return columns, data


def get_permitted_opportunities(filters):
	query_filters = {"company": filters.company} if filters.get("company") else {}
	return frappe.qb.get_query("Opportunity", filters=query_filters, ignore_permissions=False)
