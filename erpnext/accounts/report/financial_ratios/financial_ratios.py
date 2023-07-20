# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import add_days, flt

from erpnext.accounts.report.financial_statements import get_data, get_period_list
from erpnext.accounts.utils import get_balance_on


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
	data = get_ratios_data(filters, period_list, columns)

	return columns, data


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


def get_ratios_data(filters, period_list, columns):
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

	precision = frappe.db.get_single_value("System Settings", "float_precision")

	avg_debtors = {}
	avg_creditors = {}
	avg_stock = {}

	avg_ratio_balance(avg_debtors, "Receivable", period_list, precision, filters)
	avg_ratio_balance(avg_creditors, "Payable", period_list, precision, filters)
	avg_ratio_balance(avg_stock, "Stock", period_list, precision, filters)

	current_asset = {}
	current_liability = {}
	quick_asset = {}
	total_asset = {}
	total_liability = {}
	net_sales = {}
	total_income = {}
	total_expense = {}
	cogs = {}
	direct_expense = {}

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
			ratio_dict=direct_expense,
			total_dict=total_expense,
			account_type="Direct Expense",
			year=year,
			root_type_data=expense,
			root_type="Expense",
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
	fixed_asset_turnover_ratio = {"ratio": "Fixed Asset Turnover Ratio"}
	debtor_turnover_ratio = {"ratio": "Debtor Turnover Ratio"}
	creditor_turnover_ratio = {"ratio": "Creditor Turnover Ratio"}
	inventory_turnover_ratio = {"ratio": "Inventory Turnover Ratio"}

	for year in years:

		current_ratio[year] = calculate_ratio(current_asset[year], current_liability[year], precision)
		quick_ratio[year] = calculate_ratio(quick_asset[year], current_liability[year], precision)

		profit_after_tax = total_income[year] + total_expense[year]
		share_holder_fund = total_asset[year] - total_liability[year]

		debt_equity_ratio[year] = calculate_ratio(total_liability[year], share_holder_fund, precision)
		return_on_equity_ratio[year] = calculate_ratio(profit_after_tax, share_holder_fund, precision)

		net_profit_ratio[year] = calculate_ratio(profit_after_tax, net_sales[year], precision)
		gross_profit_ratio[year] = calculate_ratio(
			net_sales[year] - cogs[year], net_sales[year], precision
		)
		return_on_asset_ratio[year] = calculate_ratio(profit_after_tax, total_asset[year], precision)

		inventory_turnover_ratio[year] = calculate_ratio(cogs[year], avg_stock[year], precision)
		debtor_turnover_ratio[year] = calculate_ratio(net_sales[year], avg_debtors[year], precision)
		creditor_turnover_ratio[year] = calculate_ratio(
			# Multiplied with -1 as default value of expense in negative
			direct_expense[year] * -1,
			avg_creditors[year],
			precision,
		)
		fixed_asset_turnover_ratio[year] = calculate_ratio(net_sales[year], total_asset[year], precision)

	print(avg_creditors)

	data = [
		{"ratio": "Liquidity Ratios"},
		current_ratio,
		quick_ratio,
		{"ratio": "Solvency Ratios"},
		debt_equity_ratio,
		gross_profit_ratio,
		net_profit_ratio,
		return_on_asset_ratio,
		return_on_equity_ratio,
		{"ratio": "Turnover Ratios"},
		inventory_turnover_ratio,
		debtor_turnover_ratio,
		creditor_turnover_ratio,
		fixed_asset_turnover_ratio,
	]

	return data


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

			if account_type == "Cost of Goods Sold":
				if entry.get("account_type") == account_type:
					total_net += entry[year]
					ratio_dict[year] = total_net
			else:
				if entry.get("account_type") == account_type and entry.get("is_group"):
					ratio_dict[year] = entry[year]


def avg_ratio_balance(avg_value_dict, account_type, period_list, precision, filters):

	for period in period_list:
		opening_date = add_days(period["from_date"], -1)
		closing_date = period["to_date"]

		closing_balance = get_balance_on(
			date=closing_date,
			company=filters.company,
			account_type=account_type,
		)
		opening_balance = get_balance_on(
			date=opening_date,
			company=filters.company,
			account_type=account_type,
		)
		avg_value_dict[period["key"]] = flt(
			(flt(closing_balance) + flt(opening_balance)) / 2, precision=precision
		)


def calculate_ratio(value, denominator, precision):
	if denominator != 0:
		return flt(value / denominator, precision)
	return 0
