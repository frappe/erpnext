# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _


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
		{
			"label": _("Next Contact By"),
			"fieldname": "contact_by",
			"fieldtype": "Link",
			"options": "User",
			"width": 150,
		},
	]
	return columns


def get_data(filters):
	return frappe.db.sql(
		"""
		SELECT
			`tabOpportunity`.name,
			`tabOpportunity`.opportunity_from,
			`tabOpportunity`.party_name,
			`tabOpportunity`.customer_name,
			`tabOpportunity`.opportunity_type,
			`tabOpportunity`.contact_by,
			GROUP_CONCAT(`tabOpportunity Lost Reason Detail`.lost_reason separator ', ') lost_reason,
			`tabOpportunity`.sales_stage,
			`tabOpportunity`.territory
		FROM
			`tabOpportunity`
			{join}
		WHERE
			`tabOpportunity`.status = 'Lost' and `tabOpportunity`.company = %(company)s
			AND `tabOpportunity`.modified BETWEEN %(from_date)s AND %(to_date)s
			{conditions}
		GROUP BY
			`tabOpportunity`.name
		ORDER BY
			`tabOpportunity`.creation asc  """.format(
			conditions=get_conditions(filters), join=get_join(filters)
		),
		filters,
		as_dict=1,
	)


def get_conditions(filters):
	conditions = []

	if filters.get("territory"):
		conditions.append(" and `tabOpportunity`.territory=%(territory)s")

	if filters.get("opportunity_from"):
		conditions.append(" and `tabOpportunity`.opportunity_from=%(opportunity_from)s")

	if filters.get("party_name"):
		conditions.append(" and `tabOpportunity`.party_name=%(party_name)s")

	if filters.get("contact_by"):
		conditions.append(" and `tabOpportunity`.contact_by=%(contact_by)s")

	return " ".join(conditions) if conditions else ""


def get_join(filters):
	join = """LEFT JOIN `tabOpportunity Lost Reason Detail`
			ON `tabOpportunity Lost Reason Detail`.parenttype = 'Opportunity' and
			`tabOpportunity Lost Reason Detail`.parent = `tabOpportunity`.name"""

	if filters.get("lost_reason"):
		join = """JOIN `tabOpportunity Lost Reason Detail`
			ON `tabOpportunity Lost Reason Detail`.parenttype = 'Opportunity' and
			`tabOpportunity Lost Reason Detail`.parent = `tabOpportunity`.name and
			`tabOpportunity Lost Reason Detail`.lost_reason = '{0}'
			""".format(
			filters.get("lost_reason")
		)

	return join
