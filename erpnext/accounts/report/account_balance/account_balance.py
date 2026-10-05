# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _

from erpnext.accounts.utils import get_balance_on, get_fiscal_year


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data


def get_columns(filters):
	columns = [
		{
			"label": _("Account"),
			"fieldtype": "Link",
			"fieldname": "account",
			"options": "Account",
			"width": 200,
		},
		{
			"label": _("Currency"),
			"fieldtype": "Link",
			"fieldname": "currency",
			"options": "Currency",
			"hidden": 1,
			"width": 100,
		},
		{
			"label": _("Balance"),
			"fieldtype": "Currency",
			"fieldname": "balance",
			"options": "currency",
			"width": 100,
		},
	]

	return columns


def get_conditions(filters):
	conditions = {}

	if filters.account_type:
		conditions["account_type"] = filters.account_type

	if filters.company:
		conditions["company"] = filters.company

	if filters.root_type:
		conditions["root_type"] = filters.root_type

	return conditions


def get_data(filters):
	data = []
	conditions = get_conditions(filters)
	accounts = frappe.get_list(
		"Account", fields=["name", "account_currency", "report_type"], filters=conditions, order_by="name"
	)
	year_start_date = get_year_start_date(filters)

	for d in accounts:
		# income and expense balances run from the start of the fiscal year
		start_date = year_start_date if d.report_type == "Profit and Loss" else None
		balance = get_balance_on(
			d.name, date=filters.report_date, start_date=start_date, apply_gl_entry_permissions=True
		)
		row = {"account": d.name, "balance": balance, "currency": d.account_currency}

		data.append(row)

	return data


def get_year_start_date(filters: frappe._dict):
	fiscal_year = get_fiscal_year(
		filters.report_date, company=filters.company, verbose=0, raise_on_missing=False
	)
	return fiscal_year[1] if fiscal_year else None
