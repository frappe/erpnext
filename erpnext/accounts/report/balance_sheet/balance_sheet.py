# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt
from erpnext.accounts.report.financial_statements import (get_period_list, get_columns, get_data)

def execute(filters=None):
	period_list = get_period_list(filters.fiscal_year, filters.periodicity)

	asset = get_data(filters.company, "Asset", "Debit", period_list, only_current_fiscal_year=False)
	liability = get_data(filters.company, "Liability", "Credit", period_list, only_current_fiscal_year=False)
	equity = get_data(filters.company, "Equity", "Credit", period_list, only_current_fiscal_year=False)

	provisional_profit_loss = get_provisional_profit_loss(asset, liability, equity,
		period_list, filters.company)

	message = check_opening_balance(asset, liability, equity)

	data = []
	data.extend(asset or [])
	data.extend(liability or [])
	data.extend(equity or [])
	if provisional_profit_loss:
		data.append(provisional_profit_loss)

	columns = get_columns(filters.periodicity, period_list, company=filters.company)

	return columns, data, message

def get_provisional_profit_loss(asset, liability, equity, period_list, company):
	if asset and (liability or equity):
		total=0
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
				effective_liability += flt(liability[-2].get(period.key))
			if equity:
				effective_liability += flt(equity[-2].get(period.key))

			provisional_profit_loss[period.key] = flt(asset[-2].get(period.key)) - effective_liability

			if provisional_profit_loss[period.key]:
				has_value = True

			total += flt(provisional_profit_loss[period.key])
			provisional_profit_loss["total"] = total

		if has_value:
			return provisional_profit_loss

def check_opening_balance(asset, liability, equity):
	# Check if previous year balance sheet closed
	opening_balance = flt(asset[0].get("opening_balance", 0))
	if liability:
		opening_balance -= flt(liability[0].get("opening_balance", 0))
	if equity:
		opening_balance -= flt(asset[0].get("opening_balance", 0))

	if opening_balance:
		return _("Previous Financial Year is not closed")