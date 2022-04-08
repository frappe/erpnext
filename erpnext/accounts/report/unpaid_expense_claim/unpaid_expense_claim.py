# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _


def execute(filters=None):
	columns, data = [], []
	columns = get_columns()
	data = get_unclaimed_expese_claims(filters)
	return columns, data


def get_columns():
	return [
		_("Employee") + ":Link/Employee:120",
		_("Employee Name") + "::120",
		_("Expense Claim") + ":Link/Expense Claim:120",
		_("Sanctioned Amount") + ":Currency:120",
		_("Paid Amount") + ":Currency:120",
		_("Outstanding Amount") + ":Currency:150",
	]


def get_unclaimed_expese_claims(filters):
	cond = "1=1"
	if filters.get("employee"):
		cond = "ec.employee = %(employee)s"

	return frappe.db.sql(
		"""
		select
			ec.employee, ec.employee_name, ec.name, ec.total_sanctioned_amount, ec.total_amount_reimbursed,
			sum(gle.credit_in_account_currency - gle.debit_in_account_currency) as outstanding_amt
		from
			`tabExpense Claim` ec, `tabGL Entry` gle
		where
			gle.against_voucher_type = "Expense Claim" and gle.against_voucher = ec.name
			and gle.party is not null and ec.docstatus = 1 and ec.is_paid = 0 and {cond} group by ec.name
		having
			outstanding_amt > 0
	""".format(
			cond=cond
		),
		filters,
		as_list=1,
	)
