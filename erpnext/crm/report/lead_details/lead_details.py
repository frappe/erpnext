# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.query_builder.functions import Concat_ws, Date


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
		{"label": _("Lead Name"), "fieldname": "lead_name", "fieldtype": "Data", "width": 120},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 100},
		{
			"fieldname": "lead_owner",
			"label": _("Lead Owner"),
			"fieldtype": "Link",
			"options": "User",
			"width": 100,
		},
		{
			"label": _("Territory"),
			"fieldname": "territory",
			"fieldtype": "Link",
			"options": "Territory",
			"width": 100,
		},
		{"label": _("Source"), "fieldname": "utm_source", "fieldtype": "Data", "width": 120},
		{"label": _("Email"), "fieldname": "email_id", "fieldtype": "Data", "width": 120},
		{"label": _("Mobile"), "fieldname": "mobile_no", "fieldtype": "Data", "width": 120},
		{"label": _("Phone"), "fieldname": "phone", "fieldtype": "Data", "width": 120},
		{
			"label": _("Owner"),
			"fieldname": "owner",
			"fieldtype": "Link",
			"options": "user",
			"width": 120,
		},
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 120,
		},
		{"label": _("Address"), "fieldname": "address", "fieldtype": "Data", "width": 130},
		{"label": _("Postal Code"), "fieldname": "pincode", "fieldtype": "Data", "width": 90},
		{"label": _("City"), "fieldname": "city", "fieldtype": "Data", "width": 100},
		{"label": _("State/Province"), "fieldname": "state", "fieldtype": "Data", "width": 100},
		{
			"label": _("Country"),
			"fieldname": "country",
			"fieldtype": "Link",
			"options": "Country",
			"width": 100,
		},
	]
	return columns


def get_data(filters):
	lead = frappe.qb.DocType("Lead")
	address = frappe.qb.DocType("Address")
	dynamic_link = frappe.qb.DocType("Dynamic Link")

	query = (
		frappe.qb.from_(lead)
		.left_join(dynamic_link)
		.on((lead.name == dynamic_link.link_name) & (dynamic_link.parenttype == "Address"))
		.left_join(address)
		.on(address.name == dynamic_link.parent)
		.select(
			lead.name,
			lead.lead_name,
			lead.status,
			lead.lead_owner,
			lead.territory,
			lead.utm_source,
			lead.email_id,
			lead.mobile_no,
			lead.phone,
			lead.owner,
			lead.company,
			(Concat_ws(", ", address.address_line1, address.address_line2)).as_("address"),
			address.pincode,
			address.city,
			address.state,
			address.country,
		)
		.where(lead.company == filters.company)
		.where(Date(lead.creation).between(filters.from_date, filters.to_date))
	)

	if filters.get("territory"):
		query = query.where(lead.territory == filters.get("territory"))

	if filters.get("status"):
		query = query.where(lead.status == filters.get("status"))

	return query.run(as_dict=1)
