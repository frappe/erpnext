# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from erpnext.accounts.report.financial_statements import (get_period_list, get_columns, get_data)
from erpnext.accounts.report.profit_and_loss_statement.profit_and_loss_statement import get_net_profit_loss
from erpnext.accounts.utils import get_fiscal_year


def get_mapper_for(mappers, position):
	mapper_list = filter(lambda x: x['position'] == position, mappers)
	return mapper_list[0] if mapper_list else []


def execute(filters=None):
	period_list = get_period_list(filters.from_fiscal_year, filters.to_fiscal_year, 
		filters.periodicity, filters.accumulated_values, filters.company)

	# let's make sure mapper's is sorted by its 'position' field
	mappers = frappe.get_all(
		'Cash Flow Mapper', 
		fields=[
			'section_name', 'section_header', 'section_leader', 'section_footer', 
			'name', 'position'],
		order_by='position'
	)

	cash_flow_accounts = []

	for mapping in mappers:
		mapping['account_types'] = []
		doc = frappe.get_doc('Cash Flow Mapper', mapping['name'])
		mapping_names = [item.name for item in doc.accounts]

		accounts = frappe.db.sql(
			'select cfma.name, cfm.label, cfm.is_working_capital from `tabCash Flow Mapping Accounts` cfma '
			'join `tabCash Flow Mapping` cfm on cfma.parent=cfm.name '
			'where cfma.parent in %s '
			'order by cfm.is_working_capital', 
			(mapping_names,)
		)

		tmp_dict = [dict(name=account[0], label=account[1], is_working_capital=account[2]) for account in accounts]

		# ordering gets lost here
		unique_labels = sorted(
			set([(d['label'], d['is_working_capital']) for d in tmp_dict]), 
			key=lambda x: x[1]
		)
		for label in unique_labels:
			names = [d['name'] for d in tmp_dict if d['label'] == label[0]]
			mapping['account_types'].append(dict(label=label[0], names=names, is_working_capital=label[1]))

		cash_flow_accounts.append(mapping)

	# compute net profit / loss
	income = get_data(filters.company, "Income", "Credit", period_list, 
		accumulated_values=filters.accumulated_values, ignore_closing_entries=True, ignore_accumulated_values_for_fy= True)
	expense = get_data(filters.company, "Expense", "Debit", period_list, 
		accumulated_values=filters.accumulated_values, ignore_closing_entries=True, ignore_accumulated_values_for_fy= True)

	net_profit_loss = get_net_profit_loss(income, expense, period_list, filters.company)

	data = []
	company_currency = frappe.db.get_value("Company", filters.company, "default_currency")

	for cash_flow_account in cash_flow_accounts:
		has_added_working_capital_header = False
		section_data = []
		data.append({
			"account_name": cash_flow_account['section_header'], 
			"parent_account": None,
			"indent": 0.0, 
			"account": cash_flow_account['section_header']
		})

		if len(data) == 1:
			# add first net income in operations section
			if net_profit_loss:
				net_profit_loss.update({
					"indent": 1, 
					"parent_account": get_mapper_for(mappers, position=0)['section_header']
				})
				data.append(net_profit_loss)
				section_data.append(net_profit_loss)

				data.append({
					"account_name": cash_flow_account["section_leader"],
					"parent_account": None,
					"indent": 1.0,
					"account": cash_flow_account["section_leader"]
				})

		for account in cash_flow_account['account_types']:
			if account['is_working_capital'] and not has_added_working_capital_header:
				data.append({
					"account_name": 'Movement in working capital',
					"parent_account": None,
					"indent": 1.0,
					"account": ""
				})
				has_added_working_capital_header = True

			account_data = get_account_type_based_data(filters.company, 
				account['names'], period_list, filters.accumulated_values)
			if account_data['total'] != 0:
				account_data.update({
					"account_name": account['label'],
					"account": account['names'], 
					"indent": 1,
					"parent_account": cash_flow_account['section_header'],
					"currency": company_currency
				})
				data.append(account_data)
				section_data.append(account_data)

		add_total_row_account(data, section_data, cash_flow_account['section_footer'], 
			period_list, company_currency)

	add_total_row_account(data, data, _("Net Change in Cash"), period_list, company_currency)
	columns = get_columns(filters.periodicity, period_list, filters.accumulated_values, filters.company)

	return columns, data


def get_account_type_based_data(company, account_names, period_list, accumulated_values):
	data = {}
	total = 0
	for period in period_list:
		start_date = get_start_date(period, accumulated_values, company)
		gl_sum = frappe.db.sql_list("""
			select sum(credit) - sum(debit)
			from `tabGL Entry`
			where company=%s and posting_date >= %s and posting_date <= %s 
				and voucher_type != 'Period Closing Voucher'
				and account in ( SELECT name FROM tabAccount WHERE name IN %s
				OR parent_account IN %s)
		""", (company, start_date if accumulated_values else period['from_date'],
			period['to_date'], account_names, account_names))

		if gl_sum and gl_sum[0]:
			amount = gl_sum[0]
			if account_names == "Depreciation":
				amount *= -1
		else:
			amount = 0

		total += amount
		data.setdefault(period["key"], amount)

	data["total"] = total
	return data

def get_start_date(period, accumulated_values, company):
	start_date = period["year_start_date"]
	if accumulated_values:
		start_date = get_fiscal_year(period.to_date, company=company)[1]

	return start_date

def add_total_row_account(out, data, label, period_list, currency):
	total_row = {
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