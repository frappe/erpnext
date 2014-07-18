# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from erpnext.accounts.report.financial_statements import (process_filters, get_period_list, get_columns, get_data)

print_path = "accounts/report/financial_statements.html"

def execute(filters=None):
	process_filters(filters)
	period_list = get_period_list(filters.fiscal_year, filters.periodicity, from_beginning=True)

	data = []
	for (root_type, balance_must_be) in (("Asset", "Debit"), ("Liability", "Credit"), ("Equity", "Credit")):
		result = get_data(filters.company, root_type, balance_must_be, period_list, filters.depth)
		data.extend(result or [])

	columns = get_columns(period_list)

	return columns, data


