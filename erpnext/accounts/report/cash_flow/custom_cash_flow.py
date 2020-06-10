# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import add_to_date
from erpnext.accounts.report.financial_statements import (get_period_list, get_columns, get_data)
from erpnext.accounts.report.profit_and_loss_statement.profit_and_loss_statement import get_net_profit_loss


def get_mapper_for(mappers, position):
	mapper_list = list(filter(lambda x: x['position'] == position, mappers))
	return mapper_list[0] if mapper_list else []


def get_mappers_from_db():
	return frappe.get_all(
		'Cash Flow Mapper',
		fields=[
			'section_name', 'section_header', 'section_leader', 'section_subtotal',
			'section_footer', 'name', 'position'],
		order_by='position'
	)


def get_accounts_in_mappers(mapping_names):
	return frappe.db.sql('''
		select cfma.name, cfm.label, cfm.is_working_capital, cfm.is_income_tax_liability,
		cfm.is_income_tax_expense, cfm.is_finance_cost, cfm.is_finance_cost_adjustment
		from `tabCash Flow Mapping Accounts` cfma
		join `tabCash Flow Mapping` cfm on cfma.parent=cfm.name
		where cfma.parent in (%s)
		order by cfm.is_working_capital
	''', (', '.join(['"%s"' % d for d in mapping_names])))


def setup_mappers(mappers):
	cash_flow_accounts = []

	for mapping in mappers:
		mapping['account_types'] = []
		mapping['tax_liabilities'] = []
		mapping['tax_expenses'] = []
		mapping['finance_costs'] = []
		mapping['finance_costs_adjustments'] = []
		doc = frappe.get_doc('Cash Flow Mapper', mapping['name'])
		mapping_names = [item.name for item in doc.accounts]

		if not mapping_names:
			continue

		accounts = get_accounts_in_mappers(mapping_names)

		account_types = [
			dict(
				name=account[0], label=account[1], is_working_capital=account[2],
				is_income_tax_liability=account[3], is_income_tax_expense=account[4]
			) for account in accounts if not account[3]]

		finance_costs_adjustments = [
			dict(
				name=account[0], label=account[1], is_finance_cost=account[5],
				is_finance_cost_adjustment=account[6]
			) for account in accounts if account[6]]

		tax_liabilities = [
			dict(
				name=account[0], label=account[1], is_income_tax_liability=account[3],
				is_income_tax_expense=account[4]
			) for account in accounts if account[3]]

		tax_expenses = [
			dict(
				name=account[0], label=account[1], is_income_tax_liability=account[3],
				is_income_tax_expense=account[4]
			) for account in accounts if account[4]]

		finance_costs = [
			dict(
				name=account[0], label=account[1], is_finance_cost=account[5])
			for account in accounts if account[5]]

		account_types_labels = sorted(
			set(
				[(d['label'], d['is_working_capital'], d['is_income_tax_liability'], d['is_income_tax_expense'])
					for d in account_types]
			),
			key=lambda x: x[1]
		)

		fc_adjustment_labels = sorted(
			set(
				[(d['label'], d['is_finance_cost'], d['is_finance_cost_adjustment'])
					for d in finance_costs_adjustments if d['is_finance_cost_adjustment']]
			),
			key=lambda x: x[2]
		)

		unique_liability_labels = sorted(
			set(
				[(d['label'], d['is_income_tax_liability'], d['is_income_tax_expense'])
					for d in tax_liabilities]
			),
			key=lambda x: x[0]
		)

		unique_expense_labels = sorted(
			set(
				[(d['label'], d['is_income_tax_liability'], d['is_income_tax_expense'])
					for d in tax_expenses]
			),
			key=lambda x: x[0]
		)

		unique_finance_costs_labels = sorted(
			set(
				[(d['label'], d['is_finance_cost']) for d in finance_costs]
			),
			key=lambda x: x[0]
		)

		for label in account_types_labels:
			names = [d['name'] for d in account_types if d['label'] == label[0]]
			m = dict(label=label[0], names=names, is_working_capital=label[1])
			mapping['account_types'].append(m)

		for label in fc_adjustment_labels:
			names = [d['name'] for d in finance_costs_adjustments if d['label'] == label[0]]
			m = dict(label=label[0], names=names)
			mapping['finance_costs_adjustments'].append(m)

		for label in unique_liability_labels:
			names = [d['name'] for d in tax_liabilities if d['label'] == label[0]]
			m = dict(label=label[0], names=names, tax_liability=label[1], tax_expense=label[2])
			mapping['tax_liabilities'].append(m)

		for label in unique_expense_labels:
			names = [d['name'] for d in tax_expenses if d['label'] == label[0]]
			m = dict(label=label[0], names=names, tax_liability=label[1], tax_expense=label[2])
			mapping['tax_expenses'].append(m)

		for label in unique_finance_costs_labels:
			names = [d['name'] for d in finance_costs if d['label'] == label[0]]
			m = dict(label=label[0], names=names, is_finance_cost=label[1])
			mapping['finance_costs'].append(m)

		cash_flow_accounts.append(mapping)

	return cash_flow_accounts


def add_data_for_operating_activities(
	filters, company_currency, profit_data, period_list, light_mappers, mapper, data):
	has_added_working_capital_header = False
	section_data = []

	data.append({
		"account_name": mapper['section_header'],
		"parent_account": None,
		"indent": 0.0,
		"account": mapper['section_header']
	})

	if profit_data:
		profit_data.update({
			"indent": 1,
			"parent_account": get_mapper_for(light_mappers, position=0)['section_header']
		})
		data.append(profit_data)
		section_data.append(profit_data)

		data.append({
			"account_name": mapper["section_leader"],
			"parent_account": None,
			"indent": 1.0,
			"account": mapper["section_leader"]
		})

	for account in mapper['account_types']:
		if account['is_working_capital'] and not has_added_working_capital_header:
			data.append({
				"account_name": 'Movement in working capital',
				"parent_account": None,
				"indent": 1.0,
				"account": ""
			})
			has_added_working_capital_header = True

		account_data = _get_account_type_based_data(
			filters, account['names'], period_list, filters.accumulated_values)

		if not account['is_working_capital']:
			for key in account_data:
				if key != 'total':
					account_data[key] *= -1

		if account_data['total'] != 0:
			account_data.update({
				"account_name": account['label'],
				"account": account['names'],
				"indent": 1.0,
				"parent_account": mapper['section_header'],
				"currency": company_currency
			})
			data.append(account_data)
			section_data.append(account_data)

	_add_total_row_account(
		data, section_data, mapper['section_subtotal'], period_list, company_currency, indent=1)

	# calculate adjustment for tax paid and add to data
	if not mapper['tax_liabilities']:
		mapper['tax_liabilities'] = [
			dict(label='Income tax paid', names=[''], tax_liability=1, tax_expense=0)]

	for account in mapper['tax_liabilities']:
		tax_paid = calculate_adjustment(
			filters, mapper['tax_liabilities'], mapper['tax_expenses'],
			filters.accumulated_values, period_list)

		if tax_paid:
			tax_paid.update({
				'parent_account': mapper['section_header'],
				'currency': company_currency,
				'account_name': account['label'],
				'indent': 1.0
			})
			data.append(tax_paid)
			section_data.append(tax_paid)

	if not mapper['finance_costs_adjustments']:
		mapper['finance_costs_adjustments'] = [dict(label='Interest Paid', names=[''])]

	for account in mapper['finance_costs_adjustments']:
		interest_paid = calculate_adjustment(
			filters, mapper['finance_costs_adjustments'], mapper['finance_costs'],
			filters.accumulated_values, period_list
		)

		if interest_paid:
			interest_paid.update({
				'parent_account': mapper['section_header'],
				'currency': company_currency,
				'account_name': account['label'],
				'indent': 1.0
			})
			data.append(interest_paid)
			section_data.append(interest_paid)

	_add_total_row_account(
		data, section_data, mapper['section_footer'], period_list, company_currency)


def calculate_adjustment(filters, non_expense_mapper, expense_mapper, use_accumulated_values, period_list):
	liability_accounts = [d['names'] for d in non_expense_mapper]
	expense_accounts = [d['names'] for d in expense_mapper]

	non_expense_closing = _get_account_type_based_data(
		filters, liability_accounts, period_list, 0)

	non_expense_opening = _get_account_type_based_data(
		filters, liability_accounts, period_list, use_accumulated_values, opening_balances=1)

	expense_data = _get_account_type_based_data(
		filters, expense_accounts, period_list, use_accumulated_values)

	data = _calculate_adjustment(non_expense_closing, non_expense_opening, expense_data)
	return data


def _calculate_adjustment(non_expense_closing, non_expense_opening, expense_data):
	account_data = {}
	for month in non_expense_opening.keys():
		if non_expense_opening[month] and non_expense_closing[month]:
			account_data[month] = non_expense_opening[month] - expense_data[month] + non_expense_closing[month]
		elif expense_data[month]:
			account_data[month] = expense_data[month]

	return account_data


def add_data_for_other_activities(
	filters, company_currency, profit_data, period_list, light_mappers, mapper_list, data):
	for mapper in mapper_list:
		section_data = []
		data.append({
			"account_name": mapper['section_header'],
			"parent_account": None,
			"indent": 0.0,
			"account": mapper['section_header']
		})

		for account in mapper['account_types']:
			account_data = _get_account_type_based_data(filters,
				account['names'], period_list, filters.accumulated_values)
			if account_data['total'] != 0:
				account_data.update({
					"account_name": account['label'],
					"account": account['names'],
					"indent": 1,
					"parent_account": mapper['section_header'],
					"currency": company_currency
				})
				data.append(account_data)
				section_data.append(account_data)

		_add_total_row_account(data, section_data, mapper['section_footer'],
			period_list, company_currency)


def compute_data(filters, company_currency, profit_data, period_list, light_mappers, full_mapper):
	data = []

	operating_activities_mapper = get_mapper_for(light_mappers, position=0)
	other_mappers = [
		get_mapper_for(light_mappers, position=1),
		get_mapper_for(light_mappers, position=2)
	]

	if operating_activities_mapper:
		add_data_for_operating_activities(
			filters, company_currency, profit_data, period_list, light_mappers,
			operating_activities_mapper, data
		)

	if all(other_mappers):
		add_data_for_other_activities(
			filters, company_currency, profit_data, period_list, light_mappers, other_mappers, data
		)

	return data


def execute(filters=None):
	if not filters.periodicity: filters.periodicity = "Monthly"
	period_list = get_period_list(
		filters.from_fiscal_year, filters.to_fiscal_year, filters.periodicity,
		filters.accumulated_values, filters.company
	)

	mappers = get_mappers_from_db()

	cash_flow_accounts = setup_mappers(mappers)

	# compute net profit / loss
	income = get_data(
		filters.company, "Income", "Credit", period_list, filters=filters,
		accumulated_values=filters.accumulated_values, ignore_closing_entries=True,
		ignore_accumulated_values_for_fy=True
	)

	expense = get_data(
		filters.company, "Expense", "Debit", period_list, filters=filters,
		accumulated_values=filters.accumulated_values, ignore_closing_entries=True,
		ignore_accumulated_values_for_fy=True
	)

	net_profit_loss = get_net_profit_loss(income, expense, period_list, filters.company)

	company_currency = frappe.get_cached_value('Company',  filters.company,  "default_currency")

	data = compute_data(filters, company_currency, net_profit_loss, period_list, mappers, cash_flow_accounts)

	_add_total_row_account(data, data, _("Net Change in Cash"), period_list, company_currency)
	columns = get_columns(filters.periodicity, period_list, filters.accumulated_values, filters.company)

	return columns, data


def _get_account_type_based_data(filters, account_names, period_list, accumulated_values, opening_balances=0):
	from erpnext.accounts.report.cash_flow.cash_flow import get_start_date

	company = filters.company
	data = {}
	total = 0
	for period in period_list:
		start_date = get_start_date(period, accumulated_values, company)
		accounts = ', '.join(['"%s"' % d for d in account_names])

		if opening_balances:
			date_info = dict(date=start_date)
			months_map = {'Monthly': -1, 'Quarterly': -3, 'Half-Yearly': -6}
			years_map = {'Yearly': -1}

			if months_map.get(filters.periodicity):
				date_info.update(months=months_map[filters.periodicity])
			else:
				date_info.update(years=years_map[filters.periodicity])

			if accumulated_values:
				start, end = add_to_date(start_date, years=-1), add_to_date(period['to_date'], years=-1)
			else:
				start, end = add_to_date(**date_info), add_to_date(**date_info)

			gl_sum = frappe.db.sql_list("""
				select sum(credit) - sum(debit)
				from `tabGL Entry`
				where company=%s and posting_date >= %s and posting_date <= %s 
					and voucher_type != 'Period Closing Voucher'
					and account in ( SELECT name FROM tabAccount WHERE name IN (%s)
					OR parent_account IN (%s))
			""", (company, start, end, accounts, accounts))
		else:
			gl_sum = frappe.db.sql_list("""
				select sum(credit) - sum(debit)
				from `tabGL Entry`
				where company=%s and posting_date >= %s and posting_date <= %s 
					and voucher_type != 'Period Closing Voucher'
					and account in ( SELECT name FROM tabAccount WHERE name IN (%s)
					OR parent_account IN (%s))
			""", (company, start_date if accumulated_values else period['from_date'],
				period['to_date'], accounts, accounts))

		if gl_sum and gl_sum[0]:
			amount = gl_sum[0]
		else:
			amount = 0

		total += amount
		data.setdefault(period["key"], amount)

	data["total"] = total
	return data


def _add_total_row_account(out, data, label, period_list, currency, indent=0.0):
	total_row = {
		"indent": indent,
		"account_name": "'" + _("{0}").format(label) + "'",
		"account": "'" + _("{0}").format(label) + "'",
		"currency": currency
	}
	for row in data:
		if row.get("parent_account"):
			for period in period_list:
				total_row.setdefault(period.key, 0.0)
				total_row[period.key] += row.get(period.key, 0.0)

			total_row.setdefault("total", 0.0)
			total_row["total"] += row["total"]

	out.append(total_row)
	out.append({})
