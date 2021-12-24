# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _, msgprint


def execute(filters=None):
	if not filters: filters = {}

	columns = get_columns(filters)
	data = get_entries(filters)

	return columns, data

def get_columns(filters):
	if not filters.get("doctype"):
		msgprint(_("Please select the document type first"), raise_exception=1)

	columns =[
		{
			"label": _(filters["doctype"]),
			"options": filters["doctype"],
			"fieldname": "name",
			"fieldtype": "Link",
			"width": 140
		},
		{
			"label": _("Customer"),
			"options": "Customer",
			"fieldname": "customer",
			"fieldtype": "Link",
			"width": 140
		},
		{
			"label": _("Territory"),
			"options": "Territory",
			"fieldname": "territory",
			"fieldtype": "Link",
			"width": 100
		},
		{
			"label": _("Posting Date"),
			"fieldname": "posting_date",
			"fieldtype": "Date",
			"width": 100
		},
		{
			"label": _("Amount"),
			"fieldname": "amount",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"label": _("Sales Partner"),
			"options": "Sales Partner",
			"fieldname": "sales_partner",
			"fieldtype": "Link",
			"width": 140
		},
		{
			"label": _("Commission Rate %"),
			"fieldname": "commission_rate",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Total Commission"),
			"fieldname": "total_commission",
			"fieldtype": "Currency",
			"width": 120
		}
	]

	return columns

def get_entries(filters):
	date_field = ("transaction_date" if filters.get('doctype') == "Sales Order"
		else "posting_date")

	conditions = get_conditions(filters, date_field)
	entries = frappe.db.sql("""
		SELECT
			name, customer, territory, {0} as posting_date, base_net_total as amount,
			sales_partner, commission_rate, total_commission
		FROM
			`tab{1}`
		WHERE
			{2} and docstatus = 1 and sales_partner is not null
			and sales_partner != '' order by name desc, sales_partner
		""".format(date_field, filters.get('doctype'), conditions), filters, as_dict=1)

	return entries

def get_conditions(filters, date_field):
	conditions = "1=1"

	for field in ["company", "customer", "territory"]:
		if filters.get(field):
			conditions += " and {0} = %({1})s".format(field, field)

	if filters.get("sales_partner"):
		conditions += " and sales_partner = %(sales_partner)s"

	if filters.get("from_date"):
		conditions += " and {0} >= %(from_date)s".format(date_field)

	if filters.get("to_date"):
		conditions += " and {0} <= %(to_date)s".format(date_field)

	return conditions
