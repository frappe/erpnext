# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt
from erpnext.accounts.report.financial_statements import (get_period_list, get_columns, get_data)

def execute(filters=None):
	period_list = get_period_list(filters.fiscal_year, filters.periodicity, from_beginning=True)

	asset = get_data(filters.company, "Asset", "Debit", period_list, filters.accumulated_value)
	liability = get_data(filters.company, "Liability", "Credit", period_list, filters.accumulated_value)
	equity = get_data(filters.company, "Equity", "Credit", period_list, filters.accumulated_value)
	provisional_profit_loss = get_provisional_profit_loss(asset, liability, equity, 
		period_list, filters.company)

	data = []
	data.extend(asset or [])
	data.extend(liability or [])
	data.extend(equity or [])
	if provisional_profit_loss:
		data.append(provisional_profit_loss)

	columns = get_columns(filters.periodicity,period_list,filters.accumulated_value)

	return columns, data

def get_provisional_profit_loss(asset, liability, equity, period_list, company):
	if asset and (liability or equity):
		total_column=0
		provisional_profit_loss = {
			"account_name": "'" + _("Provisional Profit / Loss (Credit)") + "'",
			"account": None,
			"warn_if_negative": True,
			"currency": frappe.db.get_value("Company", company, "default_currency")
		}

		has_value = False

		for period in period_list:
			effective_liability = 0.0
			if liability:
				effective_liability += flt(liability[-2][period.key])
			if equity:
				effective_liability += flt(equity[-2][period.key])

			provisional_profit_loss[period.key] = flt(asset[-2][period.key]) - effective_liability

			if provisional_profit_loss[period.key]:
				has_value = True
			
			total_column=total_column+provisional_profit_loss[period.key]
			provisional_profit_loss["total"]=total_column

		if has_value:
			return provisional_profit_loss
