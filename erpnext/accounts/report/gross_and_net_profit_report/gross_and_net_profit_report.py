# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import copy

import frappe
from frappe import _
from frappe.utils import flt

from erpnext.accounts.report.financial_statements import get_columns, get_data, get_period_list


def execute(filters=None):
	period_list = get_period_list(filters.from_fiscal_year, filters.to_fiscal_year, filters.period_start_date,
		filters.period_end_date, filters.filter_based_on, filters.periodicity, filters.accumulated_values, filters.company)

	columns, data = [], []

	income = get_data(filters.company, "Income", "Credit", period_list, filters = filters,
		accumulated_values=filters.accumulated_values,
		ignore_closing_entries=True, ignore_accumulated_values_for_fy= True, total= False)

	expense = get_data(filters.company, "Expense", "Debit", period_list, filters=filters,
		accumulated_values=filters.accumulated_values,
		ignore_closing_entries=True, ignore_accumulated_values_for_fy= True, total= False)

	columns = get_columns(filters.periodicity, period_list, filters.accumulated_values, filters.company)


	gross_income = get_revenue(income, period_list)
	gross_expense = get_revenue(expense, period_list)

	if(len(gross_income)==0 and len(gross_expense)== 0):
		data.append({
			"account_name": "'" + _("Nothing is included in gross") + "'",
			"account": "'" + _("Nothing is included in gross") + "'"
		})
		return columns, data

	# to avoid error eg: gross_income[0] : list index out of range
	if not gross_income:
		gross_income = [{}]
	if not gross_expense:
		gross_expense = [{}]

	data.append({
		"account_name": "'" + _("Included in Gross Profit") + "'",
		"account": "'" + _("Included in Gross Profit") + "'"
	})

	data.append({})
	data.extend(gross_income or [])

	data.append({})
	data.extend(gross_expense or [])

	data.append({})
	gross_profit = get_profit(gross_income, gross_expense, period_list, filters.company, 'Gross Profit',filters.presentation_currency)
	data.append(gross_profit)

	non_gross_income = get_revenue(income, period_list, 0)
	data.append({})
	data.extend(non_gross_income or [])

	non_gross_expense = get_revenue(expense, period_list, 0)
	data.append({})
	data.extend(non_gross_expense or [])

	net_profit = get_net_profit(non_gross_income, gross_income, gross_expense, non_gross_expense, period_list, filters.company,filters.presentation_currency)
	data.append({})
	data.append(net_profit)

	return columns, data

def get_revenue(data, period_list, include_in_gross=1):
	revenue = [item for item in data if item['include_in_gross']==include_in_gross or item['is_group']==1]

	data_to_be_removed =True
	while data_to_be_removed:
		revenue, data_to_be_removed = remove_parent_with_no_child(revenue, period_list)
	revenue = adjust_account(revenue, period_list)
	return copy.deepcopy(revenue)

def remove_parent_with_no_child(data, period_list):
	data_to_be_removed = False
	for parent in data:
		if 'is_group' in parent and parent.get("is_group") == 1:
			have_child = False
			for child in data:
				if 'parent_account' in child  and child.get("parent_account") == parent.get("account"):
					have_child = True
					break

			if not have_child:
				data_to_be_removed = True
				data.remove(parent)

	return data, data_to_be_removed

def adjust_account(data, period_list, consolidated= False):
	leaf_nodes = [item for item in data if item['is_group'] == 0]
	totals = {}
	for node in leaf_nodes:
		set_total(node, node["total"], data, totals)
	for d in data:
		for period in period_list:
			key = period if consolidated else period.key
			d[key] = totals[d["account"]]
			d['total'] = totals[d["account"]]
	return data

def set_total(node, value, complete_list, totals):
	if not totals.get(node['account']):
		totals[node["account"]] = 0
	totals[node["account"]] += value

	parent = node['parent_account']
	if not parent == '':
		return set_total(next(item for item in complete_list if item['account'] == parent), value, complete_list, totals)


def get_profit(gross_income, gross_expense, period_list, company, profit_type, currency=None, consolidated=False):
	profit_loss = {
		"account_name": "'" + _(profit_type) + "'",
		"account": "'" + _(profit_type) + "'",
		"warn_if_negative": True,
		"currency": currency or frappe.get_cached_value('Company',  company,  "default_currency")
	}

	has_value = False

	for period in period_list:
		key = period if consolidated else period.key
		gross_income_for_period = flt(gross_income[0].get(key, 0)) if gross_income else 0
		gross_expense_for_period = flt(gross_expense[0].get(key, 0)) if gross_expense else 0
		profit_loss[key] = gross_income_for_period - gross_expense_for_period

		if profit_loss[key]:
			has_value=True

	if has_value:
		return profit_loss

def get_net_profit(non_gross_income, gross_income, gross_expense, non_gross_expense, period_list, company, currency=None, consolidated=False):
	profit_loss = {
		"account_name": "'" + _("Net Profit") + "'",
		"account": "'" + _("Net Profit") + "'",
		"warn_if_negative": True,
		"currency": currency or frappe.get_cached_value('Company',  company,  "default_currency")
	}

	has_value = False

	for period in period_list:
		key = period if consolidated else period.key
		gross_income_for_period = flt(gross_income[0].get(key, 0)) if gross_income else 0
		non_gross_income_for_period = flt(non_gross_income[0].get(key, 0)) if non_gross_income else 0

		gross_expense_for_period = flt(gross_expense[0].get(key, 0)) if gross_expense else 0
		non_gross_expense_for_period = flt(non_gross_expense[0].get(key, 0)) if non_gross_expense else 0

		total_income = gross_income_for_period + non_gross_income_for_period
		total_expense = gross_expense_for_period + non_gross_expense_for_period
		profit_loss[key] = flt(total_income) - flt(total_expense)

		if profit_loss[key]:
			has_value=True

	if has_value:
		return profit_loss
