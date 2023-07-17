# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

from erpnext.accounts.report.financial_statements import get_data, get_period_list


def execute(filters=None):
	filters["filter_based_on"] = "Fiscal Year"
	columns, data = [], []

	period_list = get_period_list(
		filters.from_fiscal_year,
		filters.to_fiscal_year,
		filters.period_start_date,
		filters.period_end_date,
		filters.filter_based_on,
		filters.periodicity,
		company=filters.company,
	)

	columns = get_columns(filters, period_list)

	years = []
	for c in columns:
		if not c.get("fieldname") == "ratio":
			years.append(c.get("fieldname"))

	assets = get_data(
		filters.company,
		"Asset",
		"Debit",
		period_list,
		only_current_fiscal_year=False,
		filters=filters,
	)

	liabilities = get_data(
		filters.company,
		"Liability",
		"Credit",
		period_list,
		only_current_fiscal_year=False,
		filters=filters,
	)

	income = get_data(
		filters.company,
		"Income",
		"Credit",
		period_list,
		only_current_fiscal_year=False,
		filters=filters,
	)
	expense = get_data(
		filters.company,
		"Expense",
		"Debit",
		period_list,
		only_current_fiscal_year=False,
		filters=filters,
	)
	# print(expense)

	precision = frappe.db.get_single_value("System Settings", "float_precision")

	current_asset = {}
	current_liability = {}
	quick_asset = {}
	total_asset = {}
	total_liability = {}
	net_sales = {}
	net_sales = {}
	total_income = {}
	total_expense = {}
	cogs = {}

	for year in years:
		total_quick_asset = 0
		total_net_sales = 0
		total_cogs = 0
		for asset in assets:
			if not asset.get("parent_account") and asset.get("is_group"):
				total_asset[year] = asset[year]
			if asset.get("account_type") == "Current Asset" and asset.get("is_group"):
				current_asset[year] = asset[year]
			if asset.get("account_type") in ["Bank", "Cash", "Receivable"] and not asset.get("is_group"):
				total_quick_asset += asset[year]
				quick_asset[year] = total_quick_asset

		for liability in liabilities:
			if not liability.get("parent_account") and liability.get("is_group"):
				total_liability[year] = liability[year]
			if liability.get("account_type") == "Current Liability" and liability.get("is_group"):
				current_liability[year] = liability[year]

		for i in income:
			if not i.get("parent_account") and i.get("is_group"):
				total_income[year] = i[year]
			if i.get("account_type") == "Direct Income":
				total_net_sales += i[year]
				net_sales[year] = total_net_sales

		for e in expense:
			if not e.get("parent_account") and e.get("is_group"):
				total_expense[year] = e[year]
			if e.get("account_type") == "Cost of Goods Sold":
				total_cogs += e[year]
				cogs[year] = total_cogs

	current_ratio = {"ratio": "Current Ratio"}
	quick_ratio = {"ratio": "Quick Ratio"}
	debt_equity_ratio = {"ratio": "Debt Equity Ratio"}
	gross_profit_ratio = {"ratio": "Gross Profit Ratio"}
	net_profit_ratio = {"ratio": "Net Profit Ratio"}
	return_on_asset_ratio = {"ratio": "Return on Asset Ratio"}
	return_on_equity_ratio = {"ratio": "Return on Equity Ratio"}

	for year in years:
		share_holder_fund = 0
		if current_liability[year] != 0:
			current_ratio[year] = flt(current_asset[year] / current_liability[year], precision)
			quick_ratio[year] = flt(quick_asset[year] / current_liability[year], precision=precision)
		else:
			current_ratio[year] = 0
			quick_ratio[year] = 0

		share_holder_fund = total_asset[year] - total_liability[year]
		profit_after_tax = total_income[year] + total_expense[year]

		if share_holder_fund != 0:
			debt_equity_ratio[year] = flt(total_liability[year] / share_holder_fund, precision=precision)
			return_on_equity_ratio[year] = flt(profit_after_tax / share_holder_fund, precision=precision)
		else:
			debt_equity_ratio[year] = 0
			return_on_equity_ratio[year] = 0

		if net_sales[year] != 0:
			net_profit_ratio[year] = flt(profit_after_tax / net_sales[year], precision=precision)
			gross_profit_ratio[year] = flt(
				(net_sales[year] - cogs[year]) / net_sales[year], precision=precision
			)

		else:
			net_profit_ratio[year] = 0
			gross_profit_ratio[year] = 0

		if total_asset[year] != 0:
			return_on_asset_ratio[year] = flt(profit_after_tax / total_asset[year], precision=precision)
		else:
			return_on_asset_ratio[year] = 0

	data = [
		current_ratio,
		quick_ratio,
		debt_equity_ratio,
		gross_profit_ratio,
		net_profit_ratio,
		return_on_asset_ratio,
		return_on_equity_ratio,
	]

	return columns, data

	# Net sales Direct Income
	# Liability mei account type == tax ka total is Tax
	# PAT = net income - tax


def get_year_wise_total(years, root_type):
	pass


def get_columns(filters, period_list):

	columns = [
		{
			"label": _("Ratios"),
			"fieldname": "ratio",
			"fieldtype": "Data",
			"width": 200,
		},
	]

	for period in period_list:
		columns.append(
			{
				"fieldname": period.key,
				"label": period.label,
				"fieldtype": "Float",
				"width": 150,
			}
		)

	return columns
