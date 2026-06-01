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
	for C in customers:
		if cint(C[8]) >= cint(days_since_last_order):
			C.insert(7, get_last_sales_amt(C[0], doctype))
			data.append(C)
	return columns, data


def get_sales_details(doctype):
	C = frappe.qb.DocType("Customer")
	DT = frappe.qb.DocType(doctype)

	DateDiff = CustomFunction("DATEDIFF", ["d1", "d2"])
	CurDate = CustomFunction("CURRENT_DATE", [])

	if doctype == "Sales Order":
		total_considered = Sum(
			Case()
			.when(DT.status == "Stopped", DT.base_net_total * DT.per_delivered / 100)
			.else_(DT.base_net_total)
		)
		date_col = DT.transaction_date
	else:
		total_considered = Sum(DT.base_net_total)
		date_col = DT.posting_date

	last_order_date = Max(date_col)
	days_since_last_order = DateDiff(CurDate(), last_order_date)

	return (
		frappe.qb.from_(C)
		.inner_join(DT)
		.on(C.name == DT.customer)
		.select(
			C.name,
			C.customer_name,
			C.territory,
			C.customer_group,
			Count(DT.name).distinct().as_("num_of_order"),
			Sum(DT.base_net_total).as_("total_order_value"),
			total_considered.as_("total_order_considered"),
			last_order_date.as_("last_order_date"),
			days_since_last_order.as_("days_since_last_order"),
		)
		.where(DT.docstatus == 1)
		.groupby(C.name)
		.orderby(days_since_last_order, order=frappe.qb.desc)
	).run(as_list=True)


def get_last_sales_amt(customer, doctype):
	DT = frappe.qb.DocType(doctype)
	date_col = DT.transaction_date if doctype == "Sales Order" else DT.posting_date

	res = (
		frappe.qb.from_(DT)
		.select(DT.base_net_total)
		.where((DT.customer == customer) & (DT.docstatus == 1))
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
