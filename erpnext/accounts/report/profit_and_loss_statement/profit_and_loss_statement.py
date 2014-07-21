# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt
from erpnext.accounts.report.financial_statements import (process_filters, get_period_list, get_columns, get_data)

def execute(filters=None):
	process_filters(filters)
	period_list = get_period_list(filters.fiscal_year, filters.periodicity)

	data = []
	income = get_data(filters.company, "Income", "Credit", period_list, filters.depth,
				ignore_opening_and_closing_entries=True)
	expense = get_data(filters.company, "Expense", "Debit", period_list, filters.depth,
				ignore_opening_and_closing_entries=True)
	net_total = get_net_total(income, expense, period_list)

	data.extend(income or [])
	data.extend(expense or [])
	if net_total:
		data.append(net_total)

	columns = get_columns(period_list)

	return columns, data

def get_net_total(income, expense, period_list):
	if income and expense:
		net_total = {
			"account_name": _("Net Profit / Loss"),
			"account": None
		}

		for period in period_list:
			net_total[period.key] = flt(income[-2][period.key] - expense[-2][period.key], 3)

		return net_total
