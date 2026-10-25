# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from dataclasses import dataclass

import frappe
from frappe import _
from frappe.utils import add_days, flt

from erpnext.accounts.report.financial_statements import get_data, get_period_list
from erpnext.accounts.utils import get_balance_on, get_fiscal_year


@dataclass(frozen=True)
class GroupLedgers:
	"""Finds the ledgers of a ratio group when no group account is typed with it, as in the shipped charts."""

	categories: tuple[str, ...]
	account_types: tuple[str, ...] = ()
	whole_root_if_none: bool = False

	def get_accounts(self, accounts: dict) -> set[str]:
		categories = get_account_categories(accounts)
		ledgers = {
			name
			for name, row in accounts.items()
			if not row.get("is_group") and self.matches(row, categories.get(name))
		}
		if not self.whole_root_if_none or self.has_category_accounts(accounts):
			return ledgers
		return {
			name for name, row in accounts.items() if row.get("is_group") and not row.get("parent_account")
		}

	def has_category_accounts(self, accounts: dict) -> bool:
		if not accounts:
			return False

		company = frappe.get_cached_value("Account", next(iter(accounts)), "company")
		return bool(
			frappe.db.exists("Account", {"company": company, "account_category": ("in", self.categories)})
		)

	def matches(self, row: dict, category: str | None) -> bool:
		if category:
			return category in self.categories
		return row.get("account_type") in self.account_types


GROUP_LEDGERS = {
	"Current Asset": GroupLedgers(
		categories=(
			"Cash and Cash Equivalents",
			"Trade Receivables",
			"Other Receivables",
			"Stock Assets",
			"Short-term Investments",
			"Other Current Assets",
		),
		account_types=("Bank", "Cash", "Receivable", "Stock", "Stock Delivered But Not Billed", "Tax"),
	),
	"Fixed Asset": GroupLedgers(
		categories=("Tangible Assets", "Intangible Assets"),
		account_types=("Fixed Asset", "Accumulated Depreciation", "Capital Work in Progress"),
	),
	"Current Liability": GroupLedgers(
		categories=(
			"Trade Payables",
			"Other Payables",
			"Short-term Borrowings",
			"Current Tax Liabilities",
			"Short-term Provisions",
			"Other Current Liabilities",
		),
		account_types=(
			"Payable",
			"Tax",
			"Stock Received But Not Billed",
			"Asset Received But Not Billed",
			"Service Received But Not Billed",
		),
	),
	"Direct Expense": GroupLedgers(
		categories=("Cost of Goods Sold", "Other Direct Costs"),
		account_types=("Cost of Goods Sold", "Expenses Included In Valuation", "Stock Adjustment"),
	),
	"Direct Income": GroupLedgers(categories=("Revenue from Operations",), whole_root_if_none=True),
}


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

	columns, years = get_columns(period_list)
	data = get_ratios_data(filters, period_list, years)

	return columns, data


def setup_filters(filters):
	if not filters.get("period_start_date"):
		period_start_date = get_fiscal_year(fiscal_year=filters.from_fiscal_year)[1]
		filters["period_start_date"] = period_start_date

	if not filters.get("period_end_date"):
		period_end_date = get_fiscal_year(fiscal_year=filters.to_fiscal_year)[2]
		filters["period_end_date"] = period_end_date


def get_columns(period_list):
	years = []
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
		years.append(period.key)

	return columns, years


def get_ratios_data(filters, period_list, years):
	data = []
	assets, liabilities, income, expense = get_gl_data(filters, period_list, years)

	current_asset, total_asset = {}, {}
	fixed_asset = {}
	current_liability, total_liability = {}, {}
	net_sales, total_income = {}, {}
	cogs, total_expense = {}, {}
	quick_asset = {}
	direct_expense = {}

	for year in years:
		total_quick_asset = 0
		total_net_sales = 0
		total_cogs = 0

		for d in [
			[
				current_asset,
				total_asset,
				"Current Asset",
				year,
				assets,
				"Asset",
				quick_asset,
				total_quick_asset,
			],
			[fixed_asset, total_asset, "Fixed Asset", year, assets, "Asset", {}, 0],
			[
				current_liability,
				total_liability,
				"Current Liability",
				year,
				liabilities,
				"Liability",
				{},
				0,
			],
			[cogs, total_expense, "Cost of Goods Sold", year, expense, "Expense", {}, total_cogs],
			[direct_expense, {}, "Direct Expense", year, expense, "Expense", {}, 0],
			[net_sales, total_income, "Direct Income", year, income, "Income", {}, total_net_sales],
		]:
			update_balances(d[0], d[1], d[2], d[3], d[4], d[5], d[6], d[7])
	add_liquidity_ratios(data, years, current_asset, current_liability, quick_asset)
	add_solvency_ratios(
		data, years, total_asset, total_liability, net_sales, cogs, total_income, total_expense
	)
	add_turnover_ratios(data, years, period_list, filters, fixed_asset, net_sales, cogs, direct_expense)

	return data


def get_gl_data(filters, period_list, years):
	data = {}

	for root_type, balance_must_be in [["Asset", "Debit"], ["Liability", "Credit"]]:
		data[frappe.scrub(root_type)] = get_data(
			filters.company,
			root_type,
			balance_must_be,
			period_list,
			only_current_fiscal_year=False,
			filters=filters,
		)

	# income and expense of each period only, as in the Profit and Loss Statement
	for root_type, balance_must_be in [["Income", "Credit"], ["Expense", "Debit"]]:
		data[frappe.scrub(root_type)] = get_data(
			filters.company,
			root_type,
			balance_must_be,
			period_list,
			filters=filters,
			accumulated_values=0,
			ignore_closing_entries=True,
		)

	assets, liabilities, income, expense = (
		data.get("asset"),
		data.get("liability"),
		data.get("income"),
		data.get("expense"),
	)

	return assets, liabilities, income, expense


def add_liquidity_ratios(data, years, current_asset, current_liability, quick_asset):
	precision = frappe.db.get_single_value("System Settings", "float_precision")
	data.append({"ratio": _("Liquidity Ratios")})

	ratio_data = [[_("Current Ratio"), current_asset], [_("Quick Ratio"), quick_asset]]

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
	data.append({"ratio": _("Solvency Ratios")})

	debt_equity_ratio = {"ratio": _("Debt Equity Ratio")}
	gross_profit_ratio = {"ratio": _("Gross Profit Ratio")}
	net_profit_ratio = {"ratio": _("Net Profit Ratio")}
	return_on_asset_ratio = {"ratio": _("Return on Asset Ratio")}
	return_on_equity_ratio = {"ratio": _("Return on Equity Ratio")}

	for year in years:
		profit_after_tax = flt(total_income.get(year)) - flt(total_expense.get(year))
		share_holder_fund = flt(total_asset.get(year)) - flt(total_liability.get(year))

		debt_equity_ratio[year] = calculate_ratio(total_liability.get(year), share_holder_fund, precision)
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


def add_turnover_ratios(data, years, period_list, filters, fixed_asset, net_sales, cogs, direct_expense):
	precision = frappe.db.get_single_value("System Settings", "float_precision")
	data.append({"ratio": _("Turnover Ratios")})

	avg_data = {}
	for d in ["Receivable", "Payable", "Stock"]:
		avg_data[frappe.scrub(d)] = avg_ratio_balance(d, period_list, precision, filters)

	avg_debtors, avg_stock = avg_data.get("receivable"), avg_data.get("stock")
	# payables are credit balances
	avg_creditors = {key: -flt(balance) for key, balance in avg_data.get("payable").items()}

	ratio_data = [
		[_("Fixed Asset Turnover Ratio"), net_sales, fixed_asset],
		[_("Debtor Turnover Ratio"), net_sales, avg_debtors],
		[_("Creditor Turnover Ratio"), direct_expense, avg_creditors],
		[_("Inventory Turnover Ratio"), cogs, avg_stock],
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
	group_accounts = get_group_accounts(account_type, root_type_data)

	for entry in root_type_data:
		if not entry.get("parent_account") and entry.get("is_group"):
			total_dict[year] = entry[year]

		if root_type == "Expense" and account_type == "Cost of Goods Sold":
			if entry.get("account_type") == account_type:
				total_net += entry.get(year)
				ratio_dict[year] = total_net
		elif entry.get("account") in group_accounts:
			ratio_dict[year] = flt(ratio_dict.get(year)) + flt(entry.get(year))

		if root_type in ("Asset", "Liability"):
			if entry.get("account_type") in ["Bank", "Cash", "Receivable"] and not entry.get("is_group"):
				total_net += entry.get(year)
				net_dict[year] = total_net


def get_group_accounts(account_type: str, root_type_data: list[dict]) -> set[str]:
	"""Accounts that make up a ratio group: the outermost groups typed with it, else its ledgers."""
	accounts = {entry.get("account"): entry for entry in root_type_data if entry.get("account")}
	typed_groups = {
		name for name, entry in accounts.items() if is_outermost_group_of_type(entry, account_type, accounts)
	}
	if typed_groups or account_type not in GROUP_LEDGERS:
		return typed_groups

	return GROUP_LEDGERS[account_type].get_accounts(accounts)


def is_outermost_group_of_type(entry, account_type, accounts):
	if not (entry.get("is_group") and entry.get("account_type") == account_type):
		return False

	parent = accounts.get(entry.get("parent_account"))
	while parent:
		if parent.get("is_group") and parent.get("account_type") == account_type:
			return False
		parent = accounts.get(parent.get("parent_account"))

	return True


def get_account_categories(accounts: dict) -> dict[str, str]:
	"""Category of each account, taken from its nearest parent group when the account has none."""
	if not accounts:
		return {}

	own_categories = dict(
		frappe.get_all(
			"Account",
			filters={"name": ("in", list(accounts)), "account_category": ("is", "set")},
			fields=["name", "account_category"],
			as_list=True,
		)
	)
	return {name: get_inherited_category(name, own_categories, accounts) for name in accounts}


def get_inherited_category(account: str, categories: dict, accounts: dict) -> str | None:
	while account and not categories.get(account):
		account = accounts.get(account, {}).get("parent_account")

	return categories.get(account)


def avg_ratio_balance(account_type, period_list, precision, filters):
	avg_ratio = {}
	for period in period_list:
		opening_date = add_days(period["from_date"], -1)
		closing_date = period["to_date"]

		closing_balance = get_balance_on(
			date=closing_date,
			company=filters.company,
			account_type=account_type,
			in_account_currency=False,
		)
		opening_balance = get_balance_on(
			date=opening_date,
			company=filters.company,
			account_type=account_type,
			in_account_currency=False,
		)
		avg_ratio[period["key"]] = flt((flt(closing_balance) + flt(opening_balance)) / 2, precision=precision)

	return avg_ratio


def calculate_ratio(value, denominator, precision):
	if flt(denominator):
		return flt(flt(value) / denominator, precision)
	return 0
