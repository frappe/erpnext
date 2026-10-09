# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.query_builder import Case
from frappe.query_builder.functions import Count, CurDate, DateDiff, Max, Sum
from frappe.utils import cint
from pypika import Order
from pypika.analytics import RowNumber

from erpnext.stock.doctype.company_restriction.company_restriction import get_allowed_companies_condition


def execute(filters=None):
	filters = filters or {}

	doctype = filters.get("doctype")
	if doctype not in {"Sales Order", "Sales Invoice"}:
		frappe.throw(_("Invalid value {0} for 'Doctype'").format(doctype))

	days_since_last_order = cint(filters.get("days_since_last_order"))
	if days_since_last_order <= 0:
		frappe.throw(_("'Days Since Last Order' must be greater than or equal to zero"))

	return get_columns(doctype), get_data(doctype, days_since_last_order)


def get_data(doctype, days_since_last_order):
	rows = [
		row for row in get_sales_details(doctype) if cint(row.days_since_last_order) >= days_since_last_order
	]

	last_amounts = get_last_order_amounts(doctype, [row.customer for row in rows]) if rows else {}
	for row in rows:
		row.last_order_amount = last_amounts.get(row.customer, 0)

	return rows


def get_sales_details(doctype):
	customer = frappe.qb.DocType("Customer")
	sales = frappe.qb.DocType(doctype)

	if doctype == "Sales Order":
		date_col = sales.transaction_date
		# a Closed order is only partially fulfilled, so count it pro rata by delivery
		considered = Sum(
			Case()
			.when(sales.status == "Closed", sales.base_net_total * sales.per_delivered / 100)
			.else_(sales.base_net_total)
		)
		num_of_order = Count(sales.name).distinct()
		last_order_date = Max(date_col)
	else:
		date_col = sales.posting_date
		considered = Sum(sales.base_net_total)
		# a credit note is not an order: keep it out of the count and the recency
		not_return = sales.is_return == 0
		num_of_order = Count(Case().when(not_return, sales.name)).distinct()
		last_order_date = Max(Case().when(not_return, date_col))

	days_since_last_order = DateDiff(CurDate(), last_order_date)

	query = (
		frappe.qb.from_(customer)
		.inner_join(sales)
		.on(customer.name == sales.customer)
		.select(
			customer.name.as_("customer"),
			customer.customer_name,
			customer.territory,
			customer.customer_group,
			num_of_order.as_("num_of_order"),
			Sum(sales.base_net_total).as_("total_order_value"),
			considered.as_("total_order_considered"),
			last_order_date.as_("last_order_date"),
			days_since_last_order.as_("days_since_last_order"),
		)
		.where(sales.docstatus == 1)
		.groupby(customer.name)
		.orderby(days_since_last_order, order=Order.desc)
	)

	if condition := get_allowed_companies_condition(sales.company, doctype):
		query = query.where(condition)

	return query.run(as_dict=True)


def get_last_order_amounts(doctype, customers):
	sales = frappe.qb.DocType(doctype)
	date_col = sales.transaction_date if doctype == "Sales Order" else sales.posting_date

	ranked = (
		frappe.qb.from_(sales)
		.select(
			sales.customer,
			sales.base_net_total,
			RowNumber().over(sales.customer).orderby(date_col, sales.name, order=Order.desc).as_("rn"),
		)
		.where((sales.docstatus == 1) & sales.customer.isin(customers))
	)
	if doctype == "Sales Invoice":
		ranked = ranked.where(sales.is_return == 0)
	if condition := get_allowed_companies_condition(sales.company, doctype):
		ranked = ranked.where(condition)

	ranked = ranked.as_("ranked")
	result = (
		frappe.qb.from_(ranked).select(ranked.customer, ranked.base_net_total).where(ranked.rn == 1).run()
	)

	return {customer: amount for customer, amount in result}


def get_columns(doctype):
	noun = "Order" if doctype == "Sales Order" else "Invoice"
	return [
		{
			"label": _("Customer"),
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 120,
		},
		{"label": _("Customer Name"), "fieldname": "customer_name", "fieldtype": "Data", "width": 150},
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
		{
			"label": _("Number of {0}s").format(_(noun)),
			"fieldname": "num_of_order",
			"fieldtype": "Int",
			"width": 120,
		},
		{
			"label": _("Total {0} Value").format(_(noun)),
			"fieldname": "total_order_value",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("Total {0} Considered").format(_(noun)),
			"fieldname": "total_order_considered",
			"fieldtype": "Currency",
			"width": 160,
		},
		{
			"label": _("Last {0} Amount").format(_(noun)),
			"fieldname": "last_order_amount",
			"fieldtype": "Currency",
			"width": 160,
		},
		{
			"label": _("Last {0} Date").format(_(noun)),
			"fieldname": "last_order_date",
			"fieldtype": "Date",
			"width": 140,
		},
		{
			"label": _("Days Since Last {0}").format(_(noun)),
			"fieldname": "days_since_last_order",
			"fieldtype": "Int",
			"width": 160,
		},
	]
