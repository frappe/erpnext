# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe import _
from frappe.utils import flt, cint
from erpnext.accounts.report.utils import get_currency, convert_to_presentation_currency
from erpnext.accounts.report.financial_statements import get_fiscal_year_data, sort_accounts
from erpnext.accounts.report.balance_sheet.balance_sheet import (get_provisional_profit_loss,
	check_opening_balance, get_chart_data)
from erpnext.accounts.report.profit_and_loss_statement.profit_and_loss_statement import (get_net_profit_loss,
	get_chart_data as get_pl_chart_data)
from erpnext.accounts.report.cash_flow.cash_flow import (get_cash_flow_accounts, get_account_type_based_gl_data,
	add_total_row_account)

def execute(filters=None):
	columns, data, message, chart = [], [], [], []

	if not filters.get('company'):
		return columns, data, message, chart

	fiscal_year = get_fiscal_year_data(filters.get('from_fiscal_year'), filters.get('to_fiscal_year'))
	companies_column, companies = get_companies(filters)
	columns = get_columns(companies_column)

	if filters.get('report') == "Balance Sheet":
		data, message, chart = get_balance_sheet_data(fiscal_year, companies, columns, filters)
	elif filters.get('report') == "Profit and Loss Statement":
		data, message, chart = get_profit_loss_data(fiscal_year, companies, columns, filters)
	else:
		if cint(frappe.db.get_single_value('Accounts Settings', 'use_custom_cash_flow')):
			from erpnext.accounts.report.cash_flow.custom_cash_flow import execute as execute_custom
			return execute_custom(filters=filters)

		data = get_cash_flow_data(fiscal_year, companies, filters)

	return columns, data, message, chart

def get_balance_sheet_data(fiscal_year, companies, columns, filters):
	asset = get_data(companies, "Asset", "Debit", fiscal_year, filters=filters)

	liability = get_data(companies, "Liability", "Credit", fiscal_year, filters=filters)

	equity = get_data(companies, "Equity", "Credit", fiscal_year, filters=filters)

	data = []
	data.extend(asset or [])
	data.extend(liability or [])
	data.extend(equity or [])

	company_currency = get_company_currency(filters)
	provisional_profit_loss, total_credit = get_provisional_profit_loss(asset, liability, equity,
		companies, filters.get('company'), company_currency, True)

	message, opening_balance = check_opening_balance(asset, liability, equity)

	if opening_balance and round(opening_balance,2) !=0:
		unclosed ={
			"account_name": "'" + _("Unclosed Fiscal Years Profit / Loss (Credit)") + "'",
			"account": "'" + _("Unclosed Fiscal Years Profit / Loss (Credit)") + "'",
			"warn_if_negative": True,
			"currency": company_currency
		}
		for company in companies:
			unclosed[company] = opening_balance
			if provisional_profit_loss:
				provisional_profit_loss[company] = provisional_profit_loss[company] - opening_balance

		unclosed["total"]=opening_balance
		data.append(unclosed)

	if provisional_profit_loss:
		data.append(provisional_profit_loss)
	if total_credit:
		data.append(total_credit)

	chart = get_chart_data(filters, columns, asset, liability, equity)

	return data, message, chart

def get_profit_loss_data(fiscal_year, companies, columns, filters):
	income, expense, net_profit_loss = get_income_expense_data(companies, fiscal_year, filters)

	data = []
	data.extend(income or [])
	data.extend(expense or [])
	if net_profit_loss:
		data.append(net_profit_loss)

	chart = get_pl_chart_data(filters, columns, income, expense, net_profit_loss)

	return data, None, chart

def get_income_expense_data(companies, fiscal_year, filters):
	company_currency = get_company_currency(filters)
	income = get_data(companies, "Income", "Credit", fiscal_year, filters, True)

	expense = get_data(companies, "Expense", "Debit", fiscal_year, filters, True)

	net_profit_loss = get_net_profit_loss(income, expense, companies, filters.company, company_currency, True)

	return income, expense, net_profit_loss
	
def get_cash_flow_data(fiscal_year, companies, filters):
	cash_flow_accounts = get_cash_flow_accounts()

	income, expense, net_profit_loss = get_income_expense_data(companies, fiscal_year, filters)

	data = []
	company_currency = get_company_currency(filters)

	for cash_flow_account in cash_flow_accounts:
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
					"parent_account": cash_flow_accounts[0]['section_header']
				})
				data.append(net_profit_loss)
				section_data.append(net_profit_loss)

		for account in cash_flow_account['account_types']:
			account_data = get_account_type_based_data(account['account_type'], companies, fiscal_year)
			account_data.update({
				"account_name": account['label'],
				"account": account['label'],
				"indent": 1,
				"parent_account": cash_flow_account['section_header'],
				"currency": company_currency
			})
			data.append(account_data)
			section_data.append(account_data)

		add_total_row_account(data, section_data, cash_flow_account['section_footer'],
			companies, company_currency, True)

	add_total_row_account(data, data, _("Net Change in Cash"), companies, company_currency, True)

	return data

def get_account_type_based_data(account_type, companies, fiscal_year):
	data = {}
	total = 0
	for company in companies:
		amount = get_account_type_based_gl_data(company,
			fiscal_year.year_start_date, fiscal_year.year_end_date, account_type)

		if amount and account_type == "Depreciation":
			amount *= -1

		total += amount
		data.setdefault(company, amount)

	data["total"] = total
	return data

def get_columns(companies):
	columns = [{
		"fieldname": "account",
		"label": _("Account"),
		"fieldtype": "Link",
		"options": "Account",
		"width": 300
	}]

	columns.append({
		"fieldname": "currency",
		"label": _("Currency"),
		"fieldtype": "Link",
		"options": "Currency",
		"hidden": 1
	})

	for company in companies:
		columns.append({
			"fieldname": company,
			"label": company,
			"fieldtype": "Currency",
			"options": "currency",
			"width": 150
		})

	return columns

def get_data(companies, root_type, balance_must_be, fiscal_year, filters=None, ignore_closing_entries=False):
	accounts, accounts_by_name = get_account_heads(root_type,
		companies, filters)

	if not accounts: return []

	company_currency = get_company_currency(filters)

	gl_entries_by_account = {}
	for root in frappe.db.sql("""select lft, rgt from tabAccount
			where root_type=%s and ifnull(parent_account, '') = ''""", root_type, as_dict=1):

		set_gl_entries_by_account(fiscal_year.year_start_date,
			fiscal_year.year_end_date, root.lft, root.rgt, filters,
			gl_entries_by_account, accounts_by_name, ignore_closing_entries=False)

	calculate_values(accounts_by_name, gl_entries_by_account, companies, fiscal_year, filters)
	accumulate_values_into_parents(accounts, accounts_by_name, companies)
	out = prepare_data(accounts, fiscal_year, balance_must_be, companies, company_currency)

	if out:
		add_total_row(out, root_type, balance_must_be, companies, company_currency)

	return out

def get_company_currency(filters=None):
	return (filters.get('presentation_currency')
		or frappe.get_cached_value('Company',  filters.company,  "default_currency"))

def calculate_values(accounts_by_name, gl_entries_by_account, companies, fiscal_year, filters):
	for entries in gl_entries_by_account.values():
		for entry in entries:
			key = entry.account_number or entry.account_name
			d = accounts_by_name.get(key)
			if d:
				for company in companies:
					# check if posting date is within the period
					if (entry.company == company or (filters.get('accumulated_in_group_company'))
						and entry.company in companies.get(company)):
						d[company] = d.get(company, 0.0) + flt(entry.debit) - flt(entry.credit)

				if entry.posting_date < fiscal_year.year_start_date:
					d["opening_balance"] = d.get("opening_balance", 0.0) + flt(entry.debit) - flt(entry.credit)

def accumulate_values_into_parents(accounts, accounts_by_name, companies):
	"""accumulate children's values in parent accounts"""
	for d in reversed(accounts):
		if d.parent_account:
			account = d.parent_account.split('-')[0].strip()
			if not accounts_by_name.get(account):
				continue

			for company in companies:
				accounts_by_name[account][company] = \
					accounts_by_name[account].get(company, 0.0) + d.get(company, 0.0)

			accounts_by_name[account]["opening_balance"] = \
				accounts_by_name[account].get("opening_balance", 0.0) + d.get("opening_balance", 0.0)

def get_account_heads(root_type, companies, filters):
	accounts = get_accounts(root_type, filters)

	if not accounts:
		return None, None

	accounts, accounts_by_name, parent_children_map = filter_accounts(accounts)

	return accounts, accounts_by_name

def get_companies(filters):
	companies = {}
	all_companies = get_subsidiary_companies(filters.get('company'))
	companies.setdefault(filters.get('company'), all_companies)

	for d in all_companies:
		if d not in companies:
			subsidiary_companies = get_subsidiary_companies(d)
			companies.setdefault(d, subsidiary_companies)

	return all_companies, companies

def get_subsidiary_companies(company):
	lft, rgt = frappe.db.get_value('Company', company,  ["lft", "rgt"])

	return frappe.db.sql_list("""select name from `tabCompany`
		where lft >= {0} and rgt <= {1} order by lft, rgt""".format(lft, rgt))

def get_accounts(root_type, filters):
	return frappe.db.sql(""" select name, is_group, company,
			parent_account, lft, rgt, root_type, report_type, account_name, account_number
		from
			`tabAccount` where company = %s and root_type = %s
		""" , (filters.get('company'), root_type), as_dict=1)

def prepare_data(accounts, fiscal_year, balance_must_be, companies, company_currency):
	data = []
	year_start_date = fiscal_year.year_start_date
	year_end_date = fiscal_year.year_end_date

	for d in accounts:
		# add to output
		has_value = False
		total = 0
		row = frappe._dict({
			"account_name": _(d.account_name),
			"account": _(d.account_name),
			"parent_account": _(d.parent_account),
			"indent": flt(d.indent),
			"year_start_date": year_start_date,
			"year_end_date": year_end_date,
			"currency": company_currency,
			"opening_balance": d.get("opening_balance", 0.0) * (1 if balance_must_be == "Debit" else -1)
		})
		for company in companies:
			if d.get(company) and balance_must_be == "Credit":
				# change sign based on Debit or Credit, since calculation is done using (debit - credit)
				d[company] *= -1

			row[company] = flt(d.get(company, 0.0), 3)

			if abs(row[company]) >= 0.005:
				# ignore zero values
				has_value = True
				total += flt(row[company])

		row["has_value"] = has_value
		row["total"] = total
		data.append(row)

	return data

def set_gl_entries_by_account(from_date, to_date, root_lft, root_rgt, filters, gl_entries_by_account,
	accounts_by_name, ignore_closing_entries=False):
	"""Returns a dict like { "account": [gl entries], ... }"""

	company_lft, company_rgt = frappe.get_cached_value('Company', 
		filters.get('company'),  ["lft", "rgt"])

	additional_conditions = get_additional_conditions(from_date, ignore_closing_entries, filters)
	companies = frappe.db.sql(""" select name, default_currency from `tabCompany`
		where lft >= %(company_lft)s and rgt <= %(company_rgt)s""", {
			"company_lft": company_lft,
			"company_rgt": company_rgt,
		}, as_dict=1)

	currency_info = frappe._dict({
		'report_date': to_date,
		'presentation_currency': filters.get('presentation_currency')
	})

	for d in companies:
		gl_entries = frappe.db.sql("""select gl.posting_date, gl.account, gl.debit, gl.credit, gl.is_opening, gl.company,
			gl.fiscal_year, gl.debit_in_account_currency, gl.credit_in_account_currency, gl.account_currency,
			acc.account_name, acc.account_number
			from `tabGL Entry` gl, `tabAccount` acc where acc.name = gl.account and gl.company = %(company)s
			{additional_conditions} and gl.posting_date <= %(to_date)s and acc.lft >= %(lft)s and acc.rgt <= %(rgt)s
			order by gl.account, gl.posting_date""".format(additional_conditions=additional_conditions),
			{
				"from_date": from_date,
				"to_date": to_date,
				"lft": root_lft,
				"rgt": root_rgt,
				"company": d.name
			},
			as_dict=True)

		if filters and filters.get('presentation_currency') != d.default_currency:
			currency_info['company'] = d.name
			currency_info['company_currency'] = d.default_currency
			convert_to_presentation_currency(gl_entries, currency_info)

		for entry in gl_entries:
			key = entry.account_number or entry.account_name
			validate_entries(key, entry, accounts_by_name)
			gl_entries_by_account.setdefault(key, []).append(entry)

	return gl_entries_by_account

def validate_entries(key, entry, accounts_by_name):
	if key not in accounts_by_name:
		field = "Account number" if entry.account_number else "Account name"
		frappe.throw(_("{0} {1} is not present in the parent company").format(field, key))

def get_additional_conditions(from_date, ignore_closing_entries, filters):
	additional_conditions = []

	if ignore_closing_entries:
		additional_conditions.append("ifnull(gl.voucher_type, '')!='Period Closing Voucher'")

	if from_date:
		additional_conditions.append("gl.posting_date >= %(from_date)s")

	company_finance_book = erpnext.get_default_finance_book(filters.get("company"))

	if not filters.get('finance_book') or (filters.get('finance_book') == company_finance_book):
		additional_conditions.append("ifnull(finance_book, '') in ('%s', '')" %
			frappe.db.escape(company_finance_book))
	elif filters.get("finance_book"):
		additional_conditions.append("ifnull(finance_book, '') = '%s' " %
			frappe.db.escape(filters.get("finance_book")))

	return " and {}".format(" and ".join(additional_conditions)) if additional_conditions else ""

def add_total_row(out, root_type, balance_must_be, companies, company_currency):
	total_row = {
		"account_name": "'" + _("Total {0} ({1})").format(_(root_type), _(balance_must_be)) + "'",
		"account": "'" + _("Total {0} ({1})").format(_(root_type), _(balance_must_be)) + "'",
		"currency": company_currency
	}

	for row in out:
		if not row.get("parent_account"):
			for company in companies:
				total_row.setdefault(company, 0.0)
				total_row[company] += row.get(company, 0.0)
				row[company] = 0.0

			total_row.setdefault("total", 0.0)
			total_row["total"] += flt(row["total"])
			row["total"] = ""

	if "total" in total_row:
		out.append(total_row)

		# blank row after Total
		out.append({})

def filter_accounts(accounts, depth=10):
	parent_children_map = {}
	accounts_by_name = {}
	for d in accounts:
		key = d.account_number or d.account_name
		accounts_by_name[key] = d
		parent_children_map.setdefault(d.parent_account or None, []).append(d)

	filtered_accounts = []

	def add_to_list(parent, level):
		if level < depth:
			children = parent_children_map.get(parent) or []
			sort_accounts(children, is_root=True if parent==None else False)

			for child in children:
				child.indent = level
				filtered_accounts.append(child)
				add_to_list(child.name, level + 1)

	add_to_list(None, 0)

	return filtered_accounts, accounts_by_name, parent_children_map
