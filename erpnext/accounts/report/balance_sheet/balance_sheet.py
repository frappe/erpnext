# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, cint
from erpnext.accounts.report.financial_statements import (get_period_list, get_columns, get_data)

def execute(filters=None):
	period_list = get_period_list(filters.from_fiscal_year, filters.to_fiscal_year, 
		filters.periodicity, company=filters.company)

	asset = get_data(filters.company, "Asset", "Debit", period_list, 
		only_current_fiscal_year=False, filters=filters,
		accumulated_values=filters.accumulated_values)
		
	liability = get_data(filters.company, "Liability", "Credit", period_list, 
		only_current_fiscal_year=False, filters=filters,
		accumulated_values=filters.accumulated_values)
		
	equity = get_data(filters.company, "Equity", "Credit", period_list, 
		only_current_fiscal_year=False, filters=filters,
		accumulated_values=filters.accumulated_values)

	provisional_profit_loss, total_credit = get_provisional_profit_loss(asset, liability, equity,
		period_list, filters.company)

	message, opening_balance = check_opening_balance(asset, liability, equity)

	data = []
	data.extend(asset or [])
	data.extend(liability or [])
	data.extend(equity or [])
	if opening_balance and round(opening_balance,2) !=0:
		unclosed ={
			"account_name": "'" + _("Unclosed Fiscal Years Profit / Loss (Credit)") + "'",
			"account": "'" + _("Unclosed Fiscal Years Profit / Loss (Credit)") + "'",
			"warn_if_negative": True,
			"currency": frappe.db.get_value("Company", filters.company, "default_currency")
		}
		for period in period_list:
			unclosed[period.key] = opening_balance
			if provisional_profit_loss:
				provisional_profit_loss[period.key] = provisional_profit_loss[period.key] - opening_balance
				
		unclosed["total"]=opening_balance
		data.append(unclosed)
		
	if provisional_profit_loss:
		data.append(provisional_profit_loss)
	if total_credit:
		data.append(total_credit)		

	columns = get_columns(filters.periodicity, period_list, filters.accumulated_values, company=filters.company)
	
	chart = get_chart_data(filters, columns, asset, liability, equity)

	return columns, data, message, chart

def get_provisional_profit_loss(asset, liability, equity, period_list, company):
	provisional_profit_loss = {}
	total_row = {}
	if asset and (liability or equity):
		total = total_row_total=0
		currency = frappe.db.get_value("Company", company, "default_currency")
		total_row = {
			"account_name": "'" + _("Total (Credit)") + "'",
			"account": "'" + _("Total (Credit)") + "'",
			"warn_if_negative": True,
			"currency": currency
		}
		has_value = False

		for period in period_list:
			effective_liability = 0.0
			if liability:
				effective_liability += flt(liability[-2].get(period.key))
			if equity:
				effective_liability += flt(equity[-2].get(period.key))

			provisional_profit_loss[period.key] = flt(asset[-2].get(period.key)) - effective_liability
			total_row[period.key] = effective_liability + provisional_profit_loss[period.key]

			if provisional_profit_loss[period.key]:
				has_value = True

			total += flt(provisional_profit_loss[period.key])
			provisional_profit_loss["total"] = total
			
			total_row_total += flt(total_row[period.key])
			total_row["total"] = total_row_total

		if has_value:
			provisional_profit_loss.update({
				"account_name": "'" + _("Provisional Profit / Loss (Credit)") + "'",
				"account": "'" + _("Provisional Profit / Loss (Credit)") + "'",
				"warn_if_negative": True,
				"currency": currency
			})
			
	return provisional_profit_loss, total_row

def check_opening_balance(asset, liability, equity):
	# Check if previous year balance sheet closed
	opening_balance = 0
	float_precision = cint(frappe.db.get_default("float_precision")) or 2
	if asset:
		opening_balance = flt(asset[0].get("opening_balance", 0), float_precision)
	if liability:
		opening_balance -= flt(liability[0].get("opening_balance", 0), float_precision)
	if equity:
		opening_balance -= flt(equity[0].get("opening_balance", 0), float_precision)
		
	opening_balance = flt(opening_balance, float_precision)
	if opening_balance:
		return _("Previous Financial Year is not closed"),opening_balance
	return None,None
		
def get_chart_data(filters, columns, asset, liability, equity):
	x_intervals = ['x'] + [d.get("label") for d in columns[2:]]
	
	asset_data, liability_data, equity_data = [], [], []
	
	for p in columns[2:]:
		if asset:
			asset_data.append(asset[-2].get(p.get("fieldname")))
		if liability:
			liability_data.append(liability[-2].get(p.get("fieldname")))
		if equity:
			equity_data.append(equity[-2].get(p.get("fieldname")))
		
	columns = [x_intervals]
	if asset_data:
		columns.append(["Assets"] + asset_data)
	if liability_data:
		columns.append(["Liabilities"] + liability_data)
	if equity_data:
		columns.append(["Equity"] + equity_data)

	chart = {
		"data": {
			'x': 'x',
			'columns': columns
		}
	}

	if not filters.accumulated_values:
		chart["chart_type"] = "bar"

	return chart