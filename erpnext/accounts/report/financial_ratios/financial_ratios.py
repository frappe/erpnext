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
	precision = frappe.db.get_single_value("System Settings", "float_precision")

	current_asset = {}
	current_liability = {}
	quick_asset = {}
	total_asset = {}
	total_liability = {}
	total_quick_asset = 0

	for y in years:
		for asset in assets:
			if not asset.get("parent_account") and asset.get("is_group"):
				total_asset[y] = asset[y]
			if asset.get("account_type") == "Current Asset" and asset.get("is_group"):
				current_asset[y] = asset[y]
			if asset.get("account_type") in ["Bank", "Cash", "Receivable"] and not asset.get("is_group"):
				total_quick_asset += asset[y]
				quick_asset[y] = total_quick_asset

		for liability in liabilities:
			if not liability.get("parent_account") and liability.get("is_group"):
				total_liability[y] = liability[y]
			if liability.get("account_type") == "Current Liability" and liability.get("is_group"):
				current_liability[y] = liability[y]

	current_ratio = {"ratio": "Current Ratio"}
	quick_ratio = {"ratio": "Quick Ratio"}
	debt_equity_ratio = {"ratio": "Debt Equity Ratio"}

	for year in years:
		share_holder_fund = 0
		if current_liability[year] != 0:
			current_ratio[year] = flt(current_asset[year] / current_liability[year], precision)
			quick_ratio[year] = flt(quick_asset[year] / current_liability[year], precision=precision)
		else:
			current_ratio[year] = 0
			quick_ratio[year] = 0

		share_holder_fund = total_asset[year] - total_liability[year]
		if share_holder_fund != 0:
			debt_equity_ratio[year] = flt(total_liability[year] / share_holder_fund, precision=precision)
		else:
			debt_equity_ratio[year] = 0

	data = [
		current_ratio,
		quick_ratio,
		debt_equity_ratio,
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
