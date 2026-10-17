# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import flt

from erpnext.selling.doctype.customer.customer import get_credit_limit, get_customer_outstanding_breakup


def execute(filters=None):
	if not filters:
		filters = {}
	# Check if customer id is according to naming series or customer name
	customer_naming_type = frappe.get_single_value("Selling Settings", "cust_master_name")
	columns = get_columns(customer_naming_type, filters.get("show_breakup"))

	data = []

	customer_list = get_details(filters)

	for d in customer_list:
		breakup = get_customer_outstanding_breakup(
			d.name, filters.get("company"), ignore_outstanding_sales_order=d.bypass_credit_limit_check
		)
		outstanding_amt = breakup.gle + breakup.sales_order + breakup.delivery_note

		credit_limit = get_credit_limit(d.name, filters.get("company"))

		bal = flt(credit_limit) - flt(outstanding_amt)

		row = [d.name]
		if customer_naming_type == "Naming Series":
			row.append(d.customer_name)

		row.append(credit_limit)
		if filters.get("show_breakup"):
			row += [breakup.gle, breakup.sales_order, breakup.delivery_note]

		row += [
			outstanding_amt,
			bal,
			d.bypass_credit_limit_check,
			d.is_frozen,
			d.disabled,
		]

		if credit_limit:
			data.append(row)

	return columns, data


def get_columns(customer_naming_type, show_breakup=False):
	columns = [
		_("Customer") + ":Link/Customer:120",
		_("Credit Limit") + ":Currency:120",
	]

	if show_breakup:
		columns += [
			_("Outstanding as per GL") + ":Currency:140",
			_("Pending Sales Orders") + ":Currency:140",
			_("Pending Delivery Notes") + ":Currency:140",
		]

	columns += [
		_("Outstanding Amt") + ":Currency:100",
		_("Credit Balance") + ":Currency:120",
		_("Bypass credit check at Sales Order") + ":Check:80",
		_("Is Frozen") + ":Check:80",
		_("Disabled") + ":Check:80",
	]

	if customer_naming_type == "Naming Series":
		columns.insert(1, _("Customer Name") + ":Data:120")

	return columns


def get_details(filters):
	company = filters.get("company")

	c = frappe.qb.DocType("Customer")
	ccl = frappe.qb.DocType("Customer Credit Limit")

	# bypass flag follows the customer's own limit row, same as credit-limit enforcement
	query = (
		frappe.qb.from_(c)
		.left_join(ccl)
		.on((ccl.parent == c.name) & (ccl.parenttype == "Customer") & (ccl.company == company))
		.select(
			c.name, c.customer_name, c.customer_group, ccl.bypass_credit_limit_check, c.is_frozen, c.disabled
		)
	)

	# customer filter is optional.
	if filters.get("customer"):
		query = query.where(c.name == filters.get("customer"))

	# without a company-wide limit, keep only customers with an own-row or group limit
	if not flt(frappe.get_cached_value("Company", company, "credit_limit")):
		gccl = frappe.qb.DocType("Customer Credit Limit").as_("gccl")
		groups_with_limit = (
			frappe.qb.from_(gccl)
			.select(gccl.parent)
			.where(
				(gccl.parenttype == "Customer Group")
				& (gccl.company == company)
				& (gccl.credit_limit > 0)
				& (gccl.bypass_credit_limit_check == 0)
			)
		)
		query = query.where(ccl.name.isnotnull() | c.customer_group.isin(groups_with_limit))

	return query.run(as_dict=1)
