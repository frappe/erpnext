# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.utils import flt

from erpnext.accounts.doctype.financial_report_template.financial_report_engine import (
	FinancialReportEngine,
	get_xlsx_styles,  #! DO NOT REMOVE - hook for styling
)
from erpnext.accounts.report.financial_statements import (
	build_period_list,
	compute_growth_view_data,
	compute_margin_view_data,
	get_columns,
	get_data,
	get_filtered_list_for_consolidated_report,
	get_period_keys_for_total,
)


def execute(filters=None):
	if filters and filters.report_template:
		return FinancialReportEngine().execute(filters)

	period_list = build_period_list(filters)

	if not period_list:
		return

	income = get_data(
		filters.company,
		"Income",
		"Credit",
		period_list,
		filters=filters,
		accumulated_values=filters.accumulated_values,
		ignore_closing_entries=True,
	)

	expense = get_data(
		filters.company,
		"Expense",
		"Debit",
		period_list,
		filters=filters,
		accumulated_values=filters.accumulated_values,
		ignore_closing_entries=True,
	)

	net_profit_loss = get_net_profit_loss(
		income,
		expense,
		period_list,
		filters.company,
		filters.presentation_currency,
		accumulated_values=bool(filters.accumulated_values),
	)

	data = []
	data.extend(income or [])
	data.extend(expense or [])
	if net_profit_loss:
		data.append(net_profit_loss)

	columns = get_columns(
		filters.periodicity,
		period_list,
		filters.accumulated_values,
		filters.company,
		selected_view=filters.get("selected_view"),
	)

	currency = filters.presentation_currency or frappe.get_cached_value(
		"Company", filters.company, "default_currency"
	)
	chart = get_chart_data(filters, period_list, income, expense, net_profit_loss, currency)

	report_summary, primitive_summary = get_report_summary(
		period_list, filters.periodicity, income, expense, net_profit_loss, currency, filters
	)

	if filters.get("selected_view") == "Growth":
		compute_growth_view_data(data, period_list)

	if filters.get("selected_view") == "Margin":
		compute_margin_view_data(data, period_list)

	return columns, data, None, chart, report_summary, primitive_summary


def get_report_summary(
	period_list,
	periodicity,
	income,
	expense,
	net_profit_loss,
	currency,
	filters,
	consolidated=False,
):
	net_income, net_expense, net_profit = 0.0, 0.0, 0.0

	# from consolidated financial statement
	if filters.get("accumulated_in_group_company"):
		period_list = get_filtered_list_for_consolidated_report(filters, period_list)
		keys = [period if consolidated else period.key for period in period_list]
	else:
		keys = get_period_keys_for_total(period_list, filters.accumulated_values, consolidated)

	# get_data() output: [...account rows..., total_row, {}]  →  [-2] = total row, [-1] = blank separator
	for key in keys:
		if income:
			net_income += flt(income[-2].get(key))
		if expense:
			net_expense += flt(expense[-2].get(key))
		if net_profit_loss:
			net_profit += flt(net_profit_loss.get(key))

	if len(period_list) == 1 and periodicity == "Yearly":
		profit_label = _("Profit This Year")
		income_label = _("Total Income This Year")
		expense_label = _("Total Expense This Year")
	else:
		profit_label = _("Net Profit")
		income_label = _("Total Income")
		expense_label = _("Total Expense")

	return [
		{"value": net_income, "label": income_label, "datatype": "Currency", "currency": currency},
		{"value": net_expense, "label": expense_label, "datatype": "Currency", "currency": currency},
		{
			"value": net_profit,
			"indicator": "Green" if net_profit > 0 else "Red",
			"label": profit_label,
			"datatype": "Currency",
			"currency": currency,
		},
	], net_profit


def get_net_profit_loss(
	income,
	expense,
	period_list,
	company,
	currency=None,
	consolidated=False,
	accumulated_values=False,
):
	net_profit_loss = {
		"account_name": "'" + _("Profit for the year") + "'",
		"account": "'" + _("Profit for the year") + "'",
		"warn_if_negative": True,
		"currency": currency or frappe.get_cached_value("Company", company, "default_currency"),
	}

	has_value = False

	for period in period_list:
		key = period if consolidated else period.key
		total_income = flt(income[-2][key], 3) if income else 0
		total_expense = flt(expense[-2][key], 3) if expense else 0

		net_profit_loss[key] = total_income - total_expense

		if net_profit_loss[key]:
			has_value = True

	total_keys = get_period_keys_for_total(period_list, accumulated_values, consolidated)

	net_profit_loss["total"] = flt(sum(net_profit_loss.get(k, 0.0) for k in total_keys))

	if has_value:
		return net_profit_loss


def get_chart_data(filters, chart_columns, income, expense, net_profit_loss, currency):
	labels = [col.get("label") for col in chart_columns]

	income_data, expense_data, net_profit = [], [], []

	for col in chart_columns:
		key = col.get("key") or col.get("fieldname")
		if income:
			income_data.append(income[-2].get(key))
		if expense:
			expense_data.append(expense[-2].get(key))
		if net_profit_loss:
			net_profit.append(net_profit_loss.get(key))

	datasets = []
	if income_data:
		datasets.append({"name": _("Income"), "values": income_data})
	if expense_data:
		datasets.append({"name": _("Expense"), "values": expense_data})
	if net_profit:
		datasets.append({"name": _("Net Profit/Loss"), "values": net_profit})

	chart = {"data": {"labels": labels, "datasets": datasets}}

	if not filters.accumulated_values:
		chart["type"] = "bar"
	else:
		chart["type"] = "line"

	chart["fieldtype"] = "Currency"
	chart["options"] = "currency"
	chart["currency"] = currency

	return chart
