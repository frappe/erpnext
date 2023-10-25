# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _, msgprint


def execute(filters=None):
	if not filters:
		filters = {}

	columns = get_columns(filters)
	entries = get_entries(filters)
	data = []

	for d in entries:
		data.append(
			[
				d.name,
				d.customer,
				d.territory,
				d.posting_date,
				d.base_net_amount,
				d.sales_person,
				d.allocated_percentage,
				d.commission_rate,
				d.allocated_amount,
				d.incentives,
			]
		)

	if data:
		total_row = [""] * len(data[0])
		data.append(total_row)

	return columns, data


def get_columns(filters):
	if not filters.get("doc_type"):
		msgprint(_("Please select the document type first"), raise_exception=1)

	columns = [
		{
			"label": _(filters["doc_type"]),
			"options": filters["doc_type"],
			"fieldname": filters["doc_type"],
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
			"label": _("Territory"),
			"options": "Territory",
			"fieldname": "territory",
			"fieldtype": "Link",
			"width": 100,
		},
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
		{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 120},
		{
			"label": _("Sales Person"),
			"options": "Sales Person",
			"fieldname": "sales_person",
			"fieldtype": "Link",
			"width": 140,
		},
		{
			"label": _("Contribution %"),
			"fieldname": "contribution_percentage",
			"fieldtype": "Data",
			"width": 110,
		},
		{
			"label": _("Commission Rate %"),
			"fieldname": "commission_rate",
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"label": _("Contribution Amount"),
			"fieldname": "contribution_amount",
			"fieldtype": "Currency",
			"width": 120,
		},
		{"label": _("Incentives"), "fieldname": "incentives", "fieldtype": "Currency", "width": 120},
	]

	return columns


def get_entries(filters):
	date_field = filters["doc_type"] == "Sales Order" and "transaction_date" or "posting_date"

	conditions, values = get_conditions(filters, date_field)
	entries = frappe.db.sql(
		"""
		select
			dt.name, dt.customer, dt.territory, dt.%s as posting_date,dt.base_net_total as base_net_amount,
			st.commission_rate,st.sales_person, st.allocated_percentage, st.allocated_amount, st.incentives
		from
			`tab%s` dt, `tabSales Team` st
		where
			st.parent = dt.name and st.parenttype = %s
			and dt.docstatus = 1 %s order by dt.name desc,st.sales_person
		"""
		% (date_field, filters["doc_type"], "%s", conditions),
		tuple([filters["doc_type"]] + values),
		as_dict=1,
	)

	return entries


def get_conditions(filters, date_field):
	conditions = [""]
	values = []

	for field in ["company", "customer", "territory"]:
		if filters.get(field):
			conditions.append("dt.{0}=%s".format(field))
			values.append(filters[field])

	if filters.get("sales_person"):
		conditions.append("st.sales_person = '{0}'".format(filters.get("sales_person")))

	if filters.get("from_date"):
		conditions.append("dt.{0}>=%s".format(date_field))
		values.append(filters["from_date"])

	if filters.get("to_date"):
		conditions.append("dt.{0}<=%s".format(date_field))
		values.append(filters["to_date"])

	return " and ".join(conditions), values
