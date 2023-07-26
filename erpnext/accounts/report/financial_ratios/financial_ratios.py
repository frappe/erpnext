# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import add_days, flt

from erpnext.accounts.report.financial_statements import get_data, get_period_list
from erpnext.accounts.utils import get_balance_on, get_fiscal_year


def execute(filters=None):
	filters["filter_based_on"] = "Fiscal Year"
	columns, data = [], []

	setup_filters(filters)

	period_list = get_period_list(
		filters.from_fiscal_year,
		filters.to_fiscal_year,
		filters.period_start_date,
		filters.period_end_date,
		filters.filter_based_on,
		filters.periodicity,
		company=filters.company,
	)

	columns = get_columns(period_list)
	data = get_ratios_data(filters, period_list, columns)

	return columns, data


def setup_filters(filters):
	if not filters.get("period_start_date"):
		period_start_date = get_fiscal_year(fiscal_year=filters.from_fiscal_year)[1]
		filters["period_start_date"] = period_start_date

	if not filters.get("period_end_date"):
		period_end_date = get_fiscal_year(fiscal_year=filters.to_fiscal_year)[2]
		filters["period_end_date"] = period_end_date


def get_columns(period_list):
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

	data = {}

	for d in [
		["Asset", "Debit"],
		["Liability", "Credit"],
		["Income", "Credit"],
		["Expense", "Debit"],
	]:
		data[frappe.scrub(d[0])] = get_data(
			filters.company,
			d[0],
			d[1],
			period_list,
			only_current_fiscal_year=False,
			filters=filters,
		)

	assets, liabilities, income, expense = (
		data.get("asset"),
		data.get("liability"),
		data.get("income"),
		data.get("expense"),
	)

	data = []

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

	add_liquidity_ratios(data, years, current_asset, current_liability, quick_asset)
	add_solvency_ratios(
		data, years, total_asset, total_liability, net_sales, cogs, total_income, total_expense
	)
	add_turnover_ratios(
		data, years, period_list, filters, total_asset, net_sales, cogs, direct_expense
	)

	return data


def add_liquidity_ratios(data, years, current_asset, current_liability, quick_asset):
	precision = frappe.db.get_single_value("System Settings", "float_precision")
	data.append({"ratio": "Liquidity Ratios"})

	ratio_data = [["Current Ratio", current_asset], ["Quick Ratio", quick_asset]]

	for d in ratio_data:
		row = {
			"ratio": d[0],
		}
		for year in years:
			row[year] = calculate_ratio(d[1].get(year, 0), current_liability.get(year, 0), precision)

		data.append(row)


def add_solvency_ratios(
	data, years, total_asset, total_liability, net_sales, cogs, total_income, total_expense
):
	precision = frappe.db.get_single_value("System Settings", "float_precision")
	data.append({"ratio": "Solvency Ratios"})

	# ratio_data = [[]]
	debt_equity_ratio = {"ratio": "Debt Equity Ratio"}
	gross_profit_ratio = {"ratio": "Gross Profit Ratio"}
	net_profit_ratio = {"ratio": "Net Profit Ratio"}
	return_on_asset_ratio = {"ratio": "Return on Asset Ratio"}
	return_on_equity_ratio = {"ratio": "Return on Equity Ratio"}

	for year in years:
		profit_after_tax = total_income[year] + total_expense[year]
		share_holder_fund = total_asset[year] - total_liability[year]

		debt_equity_ratio[year] = calculate_ratio(
			total_liability.get(year), share_holder_fund, precision
		)
		return_on_equity_ratio[year] = calculate_ratio(profit_after_tax, share_holder_fund, precision)

		net_profit_ratio[year] = calculate_ratio(profit_after_tax, net_sales.get(year), precision)
		gross_profit_ratio[year] = calculate_ratio(
			net_sales.get(year, 0) - cogs.get(year, 0), net_sales.get(year), precision
		)
		return_on_asset_ratio[year] = calculate_ratio(profit_after_tax, total_asset.get(year), precision)

	data.append(debt_equity_ratio)
	data.append(gross_profit_ratio)
	data.append(net_profit_ratio)
	data.append(return_on_asset_ratio)
	data.append(return_on_equity_ratio)


def add_turnover_ratios(
	data, years, period_list, filters, total_asset, net_sales, cogs, direct_expense
):
	precision = frappe.db.get_single_value("System Settings", "float_precision")
	data.append({"ratio": "Turnover Ratios"})

	avg_data = {}
	for d in ["Receivable", "Payable", "Stock"]:
		avg_data[frappe.scrub(d)] = avg_ratio_balance("Receivable", period_list, precision, filters)

	avg_debtors, avg_creditors, avg_stock = (
		avg_data.get("receivable"),
		avg_data.get("payable"),
		avg_data.get("stock"),
	)
	ratio_data = [
		["Fixed Asset Turnover Ratio", net_sales, total_asset],
		["Debtor Turnover Ratio", net_sales, avg_debtors],
		["Creditor Turnover Ratio", direct_expense, avg_creditors],
		["Inventory Turnover Ratio", cogs, avg_stock],
	]

	for ratio in ratio_data:
		row = {
			"ratio": ratio[0],
		}
		for year in years:
			row[year] = calculate_ratio(ratio[1].get(year, 0), ratio[2].get(year, 0), precision)

		data.append(row)


def update_balances(
	ratio_dict,
	total_dict,
	account_type,
	year,
	root_type_data,
	root_type,
	net_dict=None,
	total_net=0,
):

	for entry in root_type_data:
		if not entry.get("parent_account") and entry.get("is_group"):
			total_dict[year] = entry[year]

		if root_type in ("Asset", "Liability"):
			if entry.get("account_type") == account_type and entry.get("is_group"):
				ratio_dict[year] = entry.get(year)
			if entry.get("account_type") in ["Bank", "Cash", "Receivable"] and not entry.get("is_group"):
				total_net += entry.get(year)
				if net_dict:
					net_dict[year] = total_net
		elif root_type == "Income":
			if entry.get("account_type") == account_type and entry.get("is_group"):
				total_net += entry.get(year)
				ratio_dict[year] = total_net
		elif root_type == "Expense" and account_type == "Cost of Goods Sold":
			if entry.get("account_type") == account_type:
				total_net += entry.get(year)
				ratio_dict[year] = total_net
		else:
			if entry.get("account_type") == account_type and entry.get("is_group"):
				ratio_dict[year] = entry.get(year)


def avg_ratio_balance(account_type, period_list, precision, filters):
	avg_ratio = {}
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
		avg_ratio[period["key"]] = flt(
			(flt(closing_balance) + flt(opening_balance)) / 2, precision=precision
		)

	return avg_ratio


def calculate_ratio(value, denominator, precision):
	if flt(denominator):
		return flt(flt(value) / denominator, precision)
	return 0
