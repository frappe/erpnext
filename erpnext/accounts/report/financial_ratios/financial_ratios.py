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
	total_income = {}
	total_expense = {}
	cogs = {}

	for year in years:
		total_quick_asset = 0
		total_net_sales = 0
		total_cogs = 0

		update_balances(
			current_asset,
			total_asset,
			"Current Asset",
			year,
			assets,
			"Asset",
			quick_asset,
			total_quick_asset,
		)

		update_balances(
			current_liability, total_liability, "Current Liability", year, liabilities, "Liability"
		)

		update_balances(
			ratio_dict=cogs,
			total_dict=total_expense,
			account_type="Cost of Goods Sold",
			year=year,
			root_type_data=expense,
			root_type="Expense",
			total_net=total_cogs,
		)

		update_balances(
			ratio_dict=net_sales,
			total_dict=total_income,
			account_type="Direct Income",
			year=year,
			root_type_data=income,
			root_type="Income",
			total_net=total_net_sales,
		)

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


def update_balances(
	ratio_dict,
	total_dict,
	account_type,
	year,
	root_type_data,
	root_type,
	net_dict=None,
	total_net=None,
):

	for entry in root_type_data:
		if root_type == "Asset":
			if not entry.get("parent_account") and entry.get("is_group"):
				total_dict[year] = entry[year]
			if entry.get("account_type") == account_type and entry.get("is_group"):
				ratio_dict[year] = entry[year]
			if entry.get("account_type") in ["Bank", "Cash", "Receivable"] and not entry.get("is_group"):
				total_net += entry[year]
				net_dict[year] = total_net

		elif root_type == "Liability":
			if not entry.get("parent_account") and entry.get("is_group"):
				total_dict[year] = entry[year]
			if entry.get("account_type") == account_type and entry.get("is_group"):
				ratio_dict[year] = entry[year]

		elif root_type == "Income":
			if not entry.get("parent_account") and entry.get("is_group"):
				total_dict[year] = entry[year]

			if entry.get("account_type") == account_type and entry.get("is_group"):
				total_net += entry[year]
				ratio_dict[year] = total_net

		elif root_type == "Expense":
			if not entry.get("parent_account") and entry.get("is_group"):
				total_dict[year] = entry[year]

			if entry.get("account_type") == account_type:
				total_net += entry[year]
				ratio_dict[year] = total_net


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
