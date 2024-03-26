# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.utils import cint, cstr, flt

from erpnext.accounts.report.financial_statements import (
	get_columns,
	get_data,
	get_filtered_list_for_consolidated_report,
	get_period_list,
)


def get_all_columns(periodicity, period_list, accumulated_values=1, company=None):
	columns = [
		{
			"fieldname": "expense_account",
			"label": _("Expense"),
			"fieldtype": "Link",
			"options": "Account",
			"width": 300,
		}
	]
	if company:
		columns.append(
			{
				"fieldname": "expense_currency",
				"label": _("Currency"),
				"fieldtype": "Link",
				"options": "Currency",
				"hidden": 1,
			}
		)
	for period in period_list:
		key_name = "expense_" + cstr(period.key)
		columns.append(
			{
				"fieldname": key_name,
				"label": period.label,
				"fieldtype": "Currency",
				"options": "currency",
				"width": 150,
			}
		)
	columns.append(
		{
			"fieldname": "income_account",
			"label": _("Income"),
			"fieldtype": "Link",
			"options": "Account",
			"width": 300,
		}
	)
	if company:
		columns.append(
			{
				"fieldname": "income_currency",
				"label": _("Currency"),
				"fieldtype": "Link",
				"options": "Currency",
				"hidden": 1,
			}
		)
	for period in period_list:
		key_name = "income_" + cstr(period.key)
		columns.append(
			{
				"fieldname": key_name,
				"label": period.label,
				"fieldtype": "Currency",
				"options": "currency",
				"width": 150,
			}
		)
	if periodicity != "Yearly":
		if not accumulated_values:
			columns.append(
				{
					"fieldname": "total",
					"label": _("Total"),
					"fieldtype": "Currency",
					"width": 150,
					"options": "currency",
				}
			)
	return columns


def create_data(period_list, income, expense, income_indent, expense_indent):
	row = frappe._dict({})
	for period in period_list:
		key_name = "expense_" + cstr(period.key)
		row[key_name] = expense[period.key] if expense else ""
		key_name = "income_" + cstr(period.key)
		row[key_name] = income[period.key] if income else ""
	row["income_account"] = income["account"] if income else ""
	row["income_currency"] = income["currency"] if income else ""
	row["income_indent"] = income_indent
	row["expense_account"] = expense["account"] if expense else ""
	row["expense_currency"] = expense["currency"] if expense else ""
	row["expense_indent"] = expense_indent

	return row


def formated_data(income, expense, period_list):
	new_data = []
	i = 0
	while i < len(income) - 1 or i < len(expense) - 1:
		if i >= len(income) - 1:
			income_indent = ""
			expense_indent = (
				"&nbsp" * cint(expense[i]["indent"]) * 3
				if expense[i]["account"] != "Total Expense (Debit)"
				else ""
			)
			d = create_data(period_list, None, expense[i], income_indent, expense_indent)
		elif i >= len(expense) - 1:
			income_indent = (
				"&nbsp" * cint(income[i]["indent"]) * 3
				if income[i]["account"] != "Total Income (Credit)"
				else ""
			)
			expense_indent = ""
			d = create_data(period_list, income[i], None, income_indent, expense_indent)
		else:
			income_indent = (
				"&nbsp" * cint(income[i]["indent"]) * 3
				if income[i]["account"] != "Total Income (Credit)"
				else ""
			)
			expense_indent = (
				"&nbsp" * cint(expense[i]["indent"]) * 3
				if expense[i]["account"] != "Total Expense (Debit)"
				else ""
			)
			d = create_data(period_list, income[i], expense[i], income_indent, expense_indent)
		new_data.append(d)
		i += 1
	return new_data


def execute(filters=None):
	period_list = get_period_list(
		filters.from_fiscal_year,
		filters.to_fiscal_year,
		filters.period_start_date,
		filters.period_end_date,
		filters.filter_based_on,
		filters.periodicity,
		company=filters.company,
	)

	income = get_data(
		filters.company,
		"Income",
		"Credit",
		period_list,
		filters=filters,
		accumulated_values=filters.accumulated_values,
		ignore_closing_entries=True,
		ignore_accumulated_values_for_fy=True,
	)

	expense = get_data(
		filters.company,
		"Expense",
		"Debit",
		period_list,
		filters=filters,
		accumulated_values=filters.accumulated_values,
		ignore_closing_entries=True,
		ignore_accumulated_values_for_fy=True,
	)

	net_profit_loss = get_net_profit_loss(
		income, expense, period_list, filters.company, filters.presentation_currency
	)
	new_data = formated_data(income, expense, period_list)
	data = []
	data.extend(income or [])
	data.extend(expense or [])
	if net_profit_loss:
		row = frappe._dict({})
		for period in period_list:
			key_name = "expense_" + cstr(period.key)
			row[key_name] = net_profit_loss[period.key]
			key_name = "income_" + cstr(period.key)
			row[key_name] = net_profit_loss[period.key]
		row["income_account"] = net_profit_loss["account"]
		row["expense_account"] = net_profit_loss["account"]
		row["income_indent"] = ""
		row["expense_indent"] = ""
		new_data.append(row)

		data.append(net_profit_loss)

	if filters.report_view == "Horizontal":
		columns = get_all_columns(
			filters.periodicity, period_list, filters.accumulated_values, filters.company
		)
		data = new_data
	else:
		columns = get_columns(
			filters.periodicity, period_list, filters.accumulated_values, filters.company
		)

	chart = get_chart_data(filters, columns, income, expense, net_profit_loss)

	currency = filters.presentation_currency or frappe.get_cached_value(
		"Company", filters.company, "default_currency"
	)
	report_summary, primitive_summary = get_report_summary(
		period_list, filters.periodicity, income, expense, net_profit_loss, currency, filters
	)
	return columns, data, None, chart, report_summary, primitive_summary


def get_report_summary(
	period_list, periodicity, income, expense, net_profit_loss, currency, filters, consolidated=False
):
	net_income, net_expense, net_profit = 0.0, 0.0, 0.0

	# from consolidated financial statement
	if filters.get("accumulated_in_group_company"):
		period_list = get_filtered_list_for_consolidated_report(filters, period_list)

	if filters.accumulated_values:
		# when 'accumulated_values' is enabled, periods have running balance.
		# so, last period will have the net amount.
		key = period_list[-1].key
		if income:
			net_income = income[-2].get(key)
		if expense:
			net_expense = expense[-2].get(key)
		if net_profit_loss:
			net_profit = net_profit_loss.get(key)
	else:
		for period in period_list:
			key = period if consolidated else period.key
			if income:
				net_income += income[-2].get(key)
			if expense:
				net_expense += expense[-2].get(key)
			if net_profit_loss:
				net_profit += net_profit_loss.get(key)

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
		{"type": "separator", "value": "-"},
		{"value": net_expense, "label": expense_label, "datatype": "Currency", "currency": currency},
		{"type": "separator", "value": "=", "color": "blue"},
		{
			"value": net_profit,
			"indicator": "Green" if net_profit > 0 else "Red",
			"label": profit_label,
			"datatype": "Currency",
			"currency": currency,
		},
	], net_profit


def get_net_profit_loss(income, expense, period_list, company, currency=None, consolidated=False):
	total = 0
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

		total += flt(net_profit_loss[key])
		net_profit_loss["total"] = total

	if has_value:
		return net_profit_loss


def get_chart_data(filters, columns, income, expense, net_profit_loss):
	labels = [d.get("label") for d in columns[2:]]

	income_data, expense_data, net_profit = [], [], []

	for p in columns[2:]:
		if income:
			income_data.append(income[-2].get(p.get("fieldname")))
		if expense:
			expense_data.append(expense[-2].get(p.get("fieldname")))
		if net_profit_loss:
			net_profit.append(net_profit_loss.get(p.get("fieldname")))

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

	return chart
