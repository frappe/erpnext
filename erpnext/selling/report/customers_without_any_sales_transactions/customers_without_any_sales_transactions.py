# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from pypika.terms import ExistsCriterion

from erpnext.stock.doctype.company_restriction.company_restriction import get_allowed_masters_condition


def execute(filters=None):
	return get_columns(), get_data()


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


def get_data():
	customer = frappe.qb.DocType("Customer")
	query = (
		frappe.qb.from_(customer)
		.select(
			customer.name.as_("customer"),
			customer.customer_name,
			customer.territory,
			customer.customer_group,
		)
		.where(ExistsCriterion(get_submitted_sales(customer, "Sales Invoice")).negate())
		.where(ExistsCriterion(get_submitted_sales(customer, "Sales Order")).negate())
	)

	if condition := get_allowed_masters_condition(customer.name, "Customer"):
		query = query.where(condition)

	return query.run(as_dict=True)


def get_submitted_sales(customer, doctype):
	sales = frappe.qb.DocType(doctype)
	return (
		frappe.qb.from_(sales)
		.select(sales.name)
		.where((sales.customer == customer.name) & (sales.docstatus == 1))
	)
