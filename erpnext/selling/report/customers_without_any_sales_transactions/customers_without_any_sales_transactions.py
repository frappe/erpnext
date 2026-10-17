# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from pypika.terms import ExistsCriterion

SALES_DOCTYPES = ("Sales Invoice", "Sales Order", "Delivery Note", "POS Invoice")


def execute(filters=None):
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{
			"label": _("Customer"),
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 120,
		},
		{"label": _("Customer Name"), "fieldname": "customer_name", "fieldtype": "Data", "width": 120},
		{
			"label": _("Territory"),
			"fieldname": "territory",
			"fieldtype": "Link",
			"options": "Territory",
			"width": 120,
		},
		{
			"label": _("Customer Group"),
			"fieldname": "customer_group",
			"fieldtype": "Link",
			"options": "Customer Group",
			"width": 120,
		},
	]


def get_data(filters=None):
	company = (filters or {}).get("company")
	if company:
		# the filter is client-side only, so enforce company access on the server
		frappe.has_permission("Company", doc=company, throw=True)

	customer = frappe.qb.DocType("Customer")
	query = frappe.qb.from_(customer).select(
		customer.name.as_("customer"),
		customer.customer_name,
		customer.territory,
		customer.customer_group,
	)
	for doctype in SALES_DOCTYPES:
		query = query.where(ExistsCriterion(get_submitted_sales(customer, doctype, company)).negate())

	return query.run(as_dict=True)


def get_submitted_sales(customer, doctype, company=None):
	sales = frappe.qb.DocType(doctype)
	query = (
		frappe.qb.from_(sales)
		.select(sales.name)
		.where((sales.customer == customer.name) & (sales.docstatus == 1))
	)
	if company:
		query = query.where(sales.company == company)
	return query
