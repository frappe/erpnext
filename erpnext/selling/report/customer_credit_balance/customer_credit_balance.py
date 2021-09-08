# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import flt

from erpnext.selling.doctype.customer.customer import get_credit_limit, get_customer_outstanding


def execute(filters=None):
	if not filters: filters = {}
	#Check if customer id is according to naming series or customer name
	customer_naming_type = frappe.db.get_value("Selling Settings", None, "cust_master_name")
	columns = get_columns(customer_naming_type)

	data = []

	customer_list = get_details(filters)

	for d in customer_list:
		row = []

		outstanding_amt = get_customer_outstanding(d.name, filters.get("company"),
			ignore_outstanding_sales_order=d.bypass_credit_limit_check_at_sales_order)

		credit_limit = get_credit_limit(d.name, filters.get("company"))

		bal = flt(credit_limit) - flt(outstanding_amt)

		if customer_naming_type == "Naming Series":
			row = [d.name, d.customer_name, credit_limit, outstanding_amt, bal,
				d.bypass_credit_limit_check, d.is_frozen,
          d.disabled]
		else:
			row = [d.name, credit_limit, outstanding_amt, bal,
          d.bypass_credit_limit_check_at_sales_order, d.is_frozen, d.disabled]

		if credit_limit:
			data.append(row)

	return columns, data

def get_columns(customer_naming_type):
	columns = [
		_("Customer") + ":Link/Customer:120",
		_("Credit Limit") + ":Currency:120",
		_("Outstanding Amt") + ":Currency:100",
		_("Credit Balance") + ":Currency:120",
		_("Bypass credit check at Sales Order ") + ":Check:80",
		_("Is Frozen") + ":Check:80",
		_("Disabled") + ":Check:80",
	]

	if customer_naming_type == "Naming Series":
		columns.insert(1, _("Customer Name") + ":Data:120")

	return columns

def get_details(filters):

	sql_query = """SELECT
						c.name, c.customer_name,
						ccl.bypass_credit_limit_check,
						c.is_frozen, c.disabled
					FROM `tabCustomer` c, `tabCustomer Credit Limit` ccl
					WHERE
						c.name = ccl.parent
						AND ccl.company = %(company)s"""

	# customer filter is optional.
	if filters.get("customer"):
		sql_query += " AND c.name = %(customer)s"

	return frappe.db.sql(sql_query, filters, as_dict=1)
