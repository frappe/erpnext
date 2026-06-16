# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.query_builder import Case, CustomFunction
from frappe.query_builder.functions import Count, Max, Sum
from frappe.utils import cint


def execute(filters=None):
	if not filters:
		filters = {}

	days_since_last_order = filters.get("days_since_last_order")
	doctype = filters.get("doctype")

	if doctype not in {"Sales Order", "Sales Invoice"}:
		frappe.throw(_("Invalid value {0} for 'Doctype'").format(doctype))

	if cint(days_since_last_order) <= 0:
		frappe.throw(_("'Days Since Last Order' must be greater than or equal to zero"))

	columns = get_columns()
	customers = get_sales_details(doctype)

	data = []
	for row in customers:
		if cint(row[8]) >= cint(days_since_last_order):
			row.insert(7, get_last_sales_amt(row[0], doctype))
			data.append(row)
	return columns, data


def get_sales_details(doctype):
	customer = frappe.qb.DocType("Customer")
	sales_doctype = frappe.qb.DocType(doctype)

	date_diff = CustomFunction("DATEDIFF", ["d1", "d2"])
	current_date = CustomFunction("CURRENT_DATE", [])

	if doctype == "Sales Order":
		total_considered = Sum(
			Case()
			.when(
				sales_doctype.status == "Stopped",
				sales_doctype.base_net_total * sales_doctype.per_delivered / 100,
			)
			.else_(sales_doctype.base_net_total)
		)
		date_col = sales_doctype.transaction_date
	else:
		total_considered = Sum(sales_doctype.base_net_total)
		date_col = sales_doctype.posting_date

	last_order_date = Max(date_col)
	days_since_last_order = date_diff(current_date(), last_order_date)

	return (
		frappe.qb.from_(customer)
		.inner_join(sales_doctype)
		.on(customer.name == sales_doctype.customer)
		.select(
			customer.name,
			customer.customer_name,
			customer.territory,
			customer.customer_group,
			Count(sales_doctype.name).distinct().as_("num_of_order"),
			Sum(sales_doctype.base_net_total).as_("total_order_value"),
			total_considered.as_("total_order_considered"),
			last_order_date.as_("last_order_date"),
			days_since_last_order.as_("days_since_last_order"),
		)
		.where(sales_doctype.docstatus == 1)
		.groupby(customer.name)
		.orderby(days_since_last_order, order=frappe.qb.desc)
	).run(as_list=True)


def get_last_sales_amt(customer, doctype):
	sales_doctype = frappe.qb.DocType(doctype)
	date_col = sales_doctype.transaction_date if doctype == "Sales Order" else sales_doctype.posting_date

	res = (
		frappe.qb.from_(sales_doctype)
		.select(sales_doctype.base_net_total)
		.where((sales_doctype.customer == customer) & (sales_doctype.docstatus == 1))
		.orderby(date_col, order=frappe.qb.desc)
		.limit(1)
	).run()

	return res and res[0][0] or 0


def get_columns():
	return [
		_("Customer") + ":Link/Customer:120",
		_("Customer Name") + ":Data:120",
		_("Territory") + "::120",
		_("Customer Group") + "::120",
		_("Number of Order") + "::120",
		_("Total Order Value") + ":Currency:120",
		_("Total Order Considered") + ":Currency:160",
		_("Last Order Amount") + ":Currency:160",
		_("Last Order Date") + ":Date:160",
		_("Days Since Last Order") + "::160",
	]
