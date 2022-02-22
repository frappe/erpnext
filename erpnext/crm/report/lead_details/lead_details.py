# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.query_builder import Order
from frappe.query_builder.functions import Concat


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
	lead = frappe.qb.DocType("Lead").as_("lead")
	address = frappe.qb.DocType("Address").as_("address")
	dl = frappe.qb.DocType("Dynamic Link").as_("dl")

	query = frappe.qb.from_(lead).left_join(dl).on(
		(lead.name == dl.link_name) & (dl.parenttype == "Address")
	).left_join(address).on(
		address.name == dl.parent
	).select(
		lead.name,
		lead.lead_name,
		lead.status,
		lead.lead_owner,
		lead.territory,
		lead.source,
		lead.email_id,
		lead.mobile_no,
		lead.phone,
		lead.owner,
		lead.company,
		Concat(address.address_line1, ", ", address.address_line2).as_("address"),
		address.state,
		address.pincode,
		address.country
	).where(
		lead.creation[filters.get("from_date"):filters.get("to_date")] & lead.company==filters.get("company")
	)

	if filters.get("territory"):
		query.where(
			lead.territory == filters.get("territory")
		)
	
	if filters.get("status"):
		query.where(
			lead.territory == filters.get("status")
		)

	result = query.orderby(
		lead.creation
	).run(as_dict=True)
	
	return result