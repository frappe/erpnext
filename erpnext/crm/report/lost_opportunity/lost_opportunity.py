# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe import _
import frappe

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
			"width": 130
		},
		{
			"label": _("Party"),
			"fieldname":"party_name",
			"fieldtype": "Dynamic Link",
			"options": "opportunity_from",
			"width": 160
		},
		{
			"label": _("Customer/Lead Name"),
			"fieldname":"customer_name",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"label": _("Opportunity Type"),
			"fieldname": "opportunity_type",
			"fieldtype": "Data",
			"width": 130
		},
		{
			"label": _("Next Contact By"),
			"fieldname": "contact_by",
			"fieldtype": "Link",
			"options": "User",
			"width": 120
		}
	]
	return columns

def get_data(filters):
	return frappe.db.sql("""
		SELECT
			`tabOpportunity`.name,
			`tabOpportunity`.opportunity_from,
			`tabOpportunity`.party_name,
			`tabOpportunity`.customer_name,
			`tabOpportunity`.opportunity_type,
			`tabOpportunity`.contact_by
		FROM
			`tabOpportunity`
		WHERE
			status = 'Lost' and company = %(company)s
			{conditions}
		ORDER BY 
			creation asc """.format(conditions=get_conditions(filters)), filters, as_dict=1)

def get_conditions(filters) :
	conditions = []

	if filters.get("opportunity_from"):
		conditions.append("opportunity_from=%(opportunity_from)s")

	if filters.get("party_name"):
		conditions.append("party_name=%(party_name)s")

	if filters.get("contact_by"):
		conditions.append("contact_by=%(contact_by)s")

	return " and {}".format(" and ".join(conditions)) if conditions else ""
