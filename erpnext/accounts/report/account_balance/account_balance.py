# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _

from erpnext.accounts.utils import get_balance_on


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
			"width": 100
		},
		{
			"label": _("Currency"),
			"fieldtype": "Link",
			"fieldname": "currency",
			"options": "Currency",
			"hidden": 1,
			"width": 50
		},
		{
			"label": _("Balance"),
			"fieldtype": "Currency",
			"fieldname": "balance",
			"options": "currency",
			"width": 100
		}
	]

	return columns

def get_conditions(filters):
	conditions = {}

	if filters.account_type:
		conditions["account_type"] = filters.account_type
		return conditions

	if filters.company:
		conditions["company"] = filters.company

	if filters.root_type:
		conditions["root_type"] = filters.root_type

	return conditions

def get_data(filters):

	data = []
	conditions = get_conditions(filters)
	accounts = frappe.db.get_all("Account", fields=["name", "account_currency"],
		filters=conditions, order_by='name')

	for d in accounts:
		balance = get_balance_on(d.name, date=filters.report_date)
		row = {"account": d.name, "balance": balance, "currency": d.account_currency}

		data.append(row)

	return data
