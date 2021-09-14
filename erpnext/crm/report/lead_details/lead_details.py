# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _


def execute(filters=None):
	columns, data = get_columns(), get_data(filters)
	return columns, data

def get_columns():
	columns = [
		{
			"label": _("Lead"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Lead",
			"width": 150,
		},
		{
			"label": _("Lead Name"),
			"fieldname": "lead_name",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname":"status",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname":"lead_owner",
			"label": _("Lead Owner"),
			"fieldtype": "Link",
			"options": "User",
			"width": 100
		},
		{
			"label": _("Territory"),
			"fieldname": "territory",
			"fieldtype": "Link",
			"options": "Territory",
			"width": 100
		},
		{
			"label": _("Source"),
			"fieldname": "source",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": _("Email"),
			"fieldname": "email_id",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": _("Mobile"),
			"fieldname": "mobile_no",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": _("Phone"),
			"fieldname": "phone",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": _("Owner"),
			"fieldname": "owner",
			"fieldtype": "Link",
			"options": "user",
			"width": 120
		},
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 120
		},
		{
			"fieldname":"address",
			"label": _("Address"),
			"fieldtype": "Data",
			"width": 130
		},
		{
			"fieldname":"state",
			"label": _("State"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname":"pincode",
			"label": _("Postal Code"),
			"fieldtype": "Data",
			"width": 90
		},
		{
			"fieldname":"country",
			"label": _("Country"),
			"fieldtype": "Link",
			"options": "Country",
			"width": 100
		},

	]
	return columns

def get_data(filters):
	return frappe.db.sql("""
		SELECT
			`tabLead`.name,
			`tabLead`.lead_name,
			`tabLead`.status,
			`tabLead`.lead_owner,
			`tabLead`.territory,
			`tabLead`.source,
			`tabLead`.email_id,
			`tabLead`.mobile_no,
			`tabLead`.phone,
			`tabLead`.owner,
			`tabLead`.company,
			concat_ws(', ',
				trim(',' from `tabAddress`.address_line1),
				trim(',' from tabAddress.address_line2)
			) AS address,
			`tabAddress`.state,
			`tabAddress`.pincode,
			`tabAddress`.country
		FROM
			`tabLead` left join `tabDynamic Link` on (
			`tabLead`.name = `tabDynamic Link`.link_name and
			`tabDynamic Link`.parenttype = 'Address')
			left join `tabAddress` on (
			`tabAddress`.name=`tabDynamic Link`.parent)
		WHERE
			company = %(company)s
			AND `tabLead`.creation BETWEEN %(from_date)s AND %(to_date)s
			{conditions}
		ORDER BY
			`tabLead`.creation asc """.format(conditions=get_conditions(filters)), filters, as_dict=1)

def get_conditions(filters) :
	conditions = []

	if filters.get("territory"):
		conditions.append(" and `tabLead`.territory=%(territory)s")

	if filters.get("status"):
		conditions.append(" and `tabLead`.status=%(status)s")

	return " ".join(conditions) if conditions else ""
