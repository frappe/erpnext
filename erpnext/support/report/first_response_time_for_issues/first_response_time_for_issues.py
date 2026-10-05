# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.query_builder.functions import Avg, Date, UnixTimestamp


def execute(filters=None):
	columns = [
		{"fieldname": "creation_date", "label": _("Date"), "fieldtype": "Date", "width": 300},
		{
			"fieldname": "first_response_time",
			"fieldtype": "Duration",
			"label": _("First Response Time"),
			"width": 300,
		},
	]

	issue = frappe.qb.DocType("Issue")
	# Issues with an SLA store working time in first_response_time, so measure calendar time for all
	first_response_time = UnixTimestamp(issue.first_responded_on) - UnixTimestamp(issue.creation)
	data = (
		frappe.qb.from_(issue)
		.select(
			Date(issue.creation).as_("creation_date"),
			Avg(first_response_time).as_("avg_response_time"),
		)
		.where(
			Date(issue.creation).between(filters.from_date, filters.to_date)
			& (first_response_time > 0)
			& issue.name.isin(get_permitted_issues(filters))
		)
		.groupby(Date(issue.creation))
		.orderby(Date(issue.creation), order=frappe.qb.desc)
		.run()
	)

	return columns, data


def get_permitted_issues(filters: frappe._dict):
	company_filter = {"company": filters.company} if filters.get("company") else {}
	return frappe.qb.get_query("Issue", fields=["name"], filters=company_filter, ignore_permissions=False)
