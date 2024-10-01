# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import cint


def execute(filters=None):
	if not filters:
		filters = {}

	days_since_last_order = filters.get("days_since_last_order")
	doctype = filters.get("doctype")

	if cint(days_since_last_order) <= 0:
		frappe.throw(_("'Days Since Last Order' must be greater than or equal to zero"))

	columns = get_columns()
	customers = get_sales_details(doctype)

	data = []
	for cust in customers:
		if cint(cust[8]) >= cint(days_since_last_order):
			cust.insert(7, get_last_sales_amt(cust[0], doctype))
			data.append(cust)
	return columns, data


def get_sales_details(doctype):
	cond = """SUM(so.base_net_total) AS total_order_considered,
            MAX(so.posting_date) AS last_order_date,
            CURRENT_DATE - MAX(so.posting_date) AS days_since_last_order"""
	if doctype == "Sales Order":
		cond = """SUM(CASE WHEN so.status = 'Stopped' THEN
					so.base_net_total * so.per_delivered / 100
					ELSE so.base_net_total END) AS total_order_considered,
					MAX(so.transaction_date) AS last_order_date,
					CURRENT_DATE - MAX(so.transaction_date) AS days_since_last_order"""

	return frappe.db.sql(
		f"""SELECT
				cust.name,
				cust.customer_name,
				cust.territory,
				cust.customer_group,
				COUNT(DISTINCT so.name) AS num_of_order,
				SUM(so.base_net_total) AS total_order_value, {cond}
			FROM
				"tabCustomer" cust
			JOIN
				"tab{doctype}" so ON cust.name = so.customer
			WHERE
				so.docstatus = 1
			GROUP BY
				cust.name
			ORDER BY
				days_since_last_order DESC""",
		as_list=1,
	)

def get_last_sales_amt(customer, doctype):
	cond = "posting_date"
	if doctype == "Sales Order":
		cond = "transaction_date"
	res = frappe.db.sql(
		f"""select base_net_total from `tab{doctype}`
		where customer = %s and docstatus = 1 order by {cond} desc
		limit 1""",
		customer,
	)

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
