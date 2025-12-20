# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _, msgprint


def execute(filters=None):
	if not filters:
		filters = {}

	columns = get_columns(filters)
	data = get_entries(filters)

	return columns, data


def get_columns(filters):
	if not filters.get("doctype"):
		msgprint(_("Please select the document type first"), raise_exception=1)

	columns = [
		{
			"label": _(filters["doctype"]),
			"options": filters["doctype"],
			"fieldname": "name",
			"fieldtype": "Link",
			"width": 140,
		},
		{
			"label": _("Customer"),
			"options": "Customer",
			"fieldname": "customer",
			"fieldtype": "Link",
			"width": 140,
		},
		{
			"label": _("Currency"),
			"fieldname": "currency",
			"fieldtype": "Data",
			"width": 80,
		},
		{
			"label": _("Territory"),
			"options": "Territory",
			"fieldname": "territory",
			"fieldtype": "Link",
			"width": 100,
		},
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
		{
			"label": _("Amount"),
			"fieldname": "amount",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
		{
			"label": _("Sales Partner"),
			"options": "Sales Partner",
			"fieldname": "sales_partner",
			"fieldtype": "Link",
			"width": 140,
		},
		{
			"label": _("Commission Rate %"),
			"fieldname": "commission_rate",
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"label": _("Total Commission"),
			"fieldname": "total_commission",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
	]

	return columns


def get_entries(filters):
	date_field = "transaction_date" if filters.get("doctype") == "Sales Order" else "posting_date"
	company_currency = frappe.db.get_value("Company", filters.get("company"), "default_currency")
	conditions = get_conditions(filters, date_field)
	entries = frappe.db.sql(
		"""
		SELECT
			name, customer, territory, {} as posting_date, base_net_total as amount,
			sales_partner, commission_rate, total_commission, '{}' as currency
		FROM
			`tab{}`
		WHERE
			{} and docstatus = 1 and sales_partner is not null
			and sales_partner != '' order by name desc, sales_partner
		""".format(date_field, company_currency, filters.get("doctype"), conditions),
		filters,
		as_dict=1,
	)

	return entries


def get_conditions(filters, date_field):
	conditions = "1=1"

	for field in ["company", "customer", "territory"]:
		if filters.get(field):
			conditions += f" and {field} = %({field})s"

	if filters.get("sales_partner"):
		conditions += " and sales_partner = %(sales_partner)s"

	if filters.get("from_date"):
		conditions += f" and {date_field} >= %(from_date)s"

	if filters.get("to_date"):
		conditions += f" and {date_field} <= %(to_date)s"

	return conditions
