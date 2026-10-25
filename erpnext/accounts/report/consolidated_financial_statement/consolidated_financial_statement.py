# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from collections import defaultdict

import frappe
from frappe import _
from frappe.query_builder import Case, Criterion
from frappe.query_builder.functions import Sum
from frappe.utils import add_days, flt, getdate

import erpnext
from erpnext.accounts.report.balance_sheet.balance_sheet import (
	get_chart_data,
	get_provisional_profit_loss,
)
from erpnext.accounts.report.balance_sheet.balance_sheet import (
	get_report_summary as get_bs_summary,
)
from erpnext.accounts.report.cash_flow.cash_flow import (
	add_total_row_account,
	get_account_type_based_gl_data,
	get_cash_flow_accounts,
)
from erpnext.accounts.report.cash_flow.cash_flow import get_report_summary as get_cash_flow_summary
from erpnext.accounts.report.financial_statements import (
	filter_out_zero_value_rows,
	get_fiscal_year_data,
	sort_accounts,
)
from erpnext.accounts.report.profit_and_loss_statement.profit_and_loss_statement import (
	get_chart_data as get_pl_chart_data,
)
from erpnext.accounts.report.profit_and_loss_statement.profit_and_loss_statement import (
	get_net_profit_loss,
)
from erpnext.accounts.report.profit_and_loss_statement.profit_and_loss_statement import (
	get_report_summary as get_pl_summary,
)
from erpnext.accounts.report.utils import convert, convert_to_presentation_currency, get_rate_as_at
from erpnext.accounts.utils import get_zero_cutoff


def execute(filters=None):
	columns, data, message, chart = [], [], [], []

	if not filters.get("company"):
		return columns, data, message, chart

	fiscal_year = get_fiscal_year_data(filters.get("from_fiscal_year"), filters.get("to_fiscal_year"))
	company_list, companies = get_companies(filters)
	company_columns = get_company_columns(company_list, filters)
	columns = get_columns(company_columns)

	if filters.get("report") == "Balance Sheet":
		data, message, chart, report_summary = get_balance_sheet_data(
			fiscal_year, companies, company_columns, filters
		)
	elif filters.get("report") == "Profit and Loss Statement":
		data, message, chart, report_summary = get_profit_loss_data(
			fiscal_year, companies, company_columns, filters
		)
	else:
		data, report_summary = get_cash_flow_data(fiscal_year, companies, filters)

	return columns, data, message, chart, report_summary


def get_balance_sheet_data(fiscal_year, companies, company_columns, filters):
	translator = CurrencyTranslator(companies, filters, fiscal_year)
	translator.add_profit_and_loss_difference()

	asset = get_data(companies, "Asset", "Debit", fiscal_year, filters, translator=translator)
	liability = get_data(companies, "Liability", "Credit", fiscal_year, filters, translator=translator)
	equity = get_data(companies, "Equity", "Credit", fiscal_year, filters, translator=translator)

	data = []
	data.extend(asset or [])
	data.extend(liability or [])
	data.extend(equity or [])

	company_currency = get_company_currency(filters)
	provisional_profit_loss, total_credit = get_provisional_profit_loss(
		asset, liability, equity, companies, filters.get("company"), company_currency, True
	)

	message, opening_balance = prepare_companywise_opening_balance(asset, liability, equity, companies)

	if opening_balance:
		unclosed = {
			"account_name": "'" + _("Unclosed Fiscal Years Profit / Loss (Credit)") + "'",
			"account": "'" + _("Unclosed Fiscal Years Profit / Loss (Credit)") + "'",
			"warn_if_negative": True,
			"currency": company_currency,
		}

		for company in companies:
			unclosed[company] = opening_balance.get(company)
			if provisional_profit_loss and provisional_profit_loss.get(company):
				provisional_profit_loss[company] = flt(provisional_profit_loss[company]) - flt(
					opening_balance.get(company)
				)

		unclosed["total"] = sum(opening_balance.values())
		set_group_company_total(unclosed, filters)
		data.append(unclosed)

	set_group_company_total(provisional_profit_loss, filters)
	set_group_company_total(total_credit, filters)

	if provisional_profit_loss:
		data.append(provisional_profit_loss)
	if total_credit:
		data.append(total_credit)

	report_summary, primitive_summary = get_bs_summary(
		get_summary_companies(companies, filters),
		asset,
		liability,
		equity,
		provisional_profit_loss,
		company_currency,
		filters,
		True,
	)

	chart = get_chart_data(filters, company_columns, asset, liability, equity, company_currency)

	return data, message, chart, report_summary


def prepare_companywise_opening_balance(asset_data, liability_data, equity_data, companies):
	opening_balance = {}
	for company in companies:
		opening_value = 0

		# opening_value = Aseet - liability - equity
		for data in [asset_data, liability_data, equity_data]:
			if data:
				account_name = get_root_account_name(data[0].root_type, company)
				if account_name:
					opening_value += get_opening_balance(account_name, data, company) or 0.0

		opening_balance[company] = opening_value

	if any(flt(value, 3) for value in opening_balance.values()):
		return _("Previous Financial Year is not closed"), opening_balance

	return "", {}


def get_opening_balance(account_name, data, company):
	for row in data:
		if row.get("account_name") == account_name:
			return row.get("company_wise_opening_bal", {}).get(company, 0.0)


def get_root_account_name(root_type, company):
	root_account = frappe.get_all(
		"Account",
		fields=["account_name"],
		filters={
			"root_type": root_type,
			"is_group": 1,
			"company": company,
			"parent_account": ("is", "not set"),
		},
		as_list=1,
	)

	if root_account:
		return root_account[0][0]


def get_profit_loss_data(fiscal_year, companies, company_columns, filters):
	income, expense, net_profit_loss = get_income_expense_data(companies, fiscal_year, filters)
	company_currency = get_company_currency(filters)

	data = []
	data.extend(income or [])
	data.extend(expense or [])
	if net_profit_loss:
		data.append(net_profit_loss)

	chart = get_pl_chart_data(filters, company_columns, income, expense, net_profit_loss, company_currency)

	report_summary, primitive_summary = get_pl_summary(
		get_summary_companies(companies, filters),
		"",
		income,
		expense,
		net_profit_loss,
		company_currency,
		filters,
		True,
	)

	return data, None, chart, report_summary


def get_summary_companies(companies, filters):
	"""Company columns that can be added up in the summary cards without mixing currencies."""
	if filters.get("presentation_currency"):
		return list(companies)

	currencies = {erpnext.get_company_currency(company) for company in companies}
	return list(companies) if len(currencies) == 1 else [filters.company]


def get_income_expense_data(companies, fiscal_year, filters, translator=None):
	company_currency = get_company_currency(filters)
	translator = translator or CurrencyTranslator(companies, filters, fiscal_year)
	income = get_data(companies, "Income", "Credit", fiscal_year, filters, True, translator)
	expense = get_data(companies, "Expense", "Debit", fiscal_year, filters, True, translator)

	net_profit_loss = get_net_profit_loss(
		income,
		expense,
		companies,
		filters.company,
		company_currency,
		consolidated=True,
		accumulated_values=bool(filters.accumulated_values),
	)
	set_group_company_total(net_profit_loss, filters)

	return income, expense, net_profit_loss


def get_cash_flow_data(fiscal_year, companies, filters):
	cash_flow_accounts = get_cash_flow_accounts()

	translator = CurrencyTranslator(companies, filters, fiscal_year)
	income, expense, net_profit_loss = get_income_expense_data(companies, fiscal_year, filters, translator)
	translation_difference = get_translation_difference_row(translator, companies, filters)

	data = []
	summary_data = {}
	company_currency = get_company_currency(filters)

	for cash_flow_account in cash_flow_accounts:
		section_data = []
		data.append(
			{
				"account_name": cash_flow_account["section_header"],
				"parent_account": None,
				"indent": 0.0,
				"account": cash_flow_account["section_header"],
			}
		)

		if len(data) == 1:
			# add first net income in operations section
			if net_profit_loss:
				net_profit_loss.update(
					{"indent": 1, "parent_account": cash_flow_accounts[0]["section_header"]}
				)
				data.append(net_profit_loss)
				section_data.append(net_profit_loss)

			if translation_difference:
				translation_difference.update(
					{"currency": company_currency, "parent_account": cash_flow_accounts[0]["section_header"]}
				)
				data.append(translation_difference)
				section_data.append(translation_difference)

		for account in cash_flow_account["account_types"]:
			account_data = get_account_type_based_data(
				account["account_type"], companies, fiscal_year, filters
			)
			account_data.update(
				{
					"account_name": account["label"],
					"account": account["label"],
					"indent": 1,
					"parent_account": cash_flow_account["section_header"],
					"currency": company_currency,
				}
			)
			data.append(account_data)
			section_data.append(account_data)

		add_cash_flow_total_row(
			data,
			section_data,
			cash_flow_account["section_footer"],
			companies,
			company_currency,
			summary_data,
			filters,
		)

	add_cash_flow_total_row(
		data, data, _("Net Change in Cash"), companies, company_currency, summary_data, filters
	)

	report_summary = get_cash_flow_summary(summary_data, company_currency)

	return data, report_summary


def get_translation_difference_row(translator, companies, filters) -> dict | None:
	"""Profit is translated at the transaction rate and cash flows at the closing rate; this row reconciles them."""
	if not any(flt(amount, 3) for amount in translator.reserve.values()):
		return None

	label = _("Foreign Currency Translation Reserve")
	row = {company: -flt(translator.reserve.get(company), 3) for company in companies}
	row.update({"total": sum(row.values()), "account_name": label, "account": label, "indent": 1})
	set_group_company_total(row, filters)
	return row


def add_cash_flow_total_row(
	out: list, rows: list, label: str, companies: dict, currency: str, summary_data: dict, filters: dict
) -> None:
	"""Total every company column; the summary card shows only the group company when accumulating."""
	column_filters = frappe._dict(filters, accumulated_in_group_company=0)
	total_row = add_total_row_account(
		out, rows, label, companies, currency, summary_data, column_filters, True
	)

	if filters.get("accumulated_in_group_company"):
		summary_data[label] = total_row.get(filters.company, 0.0)


def get_account_type_based_data(account_type, companies, fiscal_year, filters):
	gl_filters = frappe._dict(filters, account_type=account_type)
	gl_filters.start_date, gl_filters.end_date = get_period_dates(fiscal_year, filters)

	own_amounts = {company: get_company_account_type_amount(company, gl_filters) for company in companies}
	data = {company: get_column_amount(company, companies, own_amounts, gl_filters) for company in companies}

	if filters.get("accumulated_in_group_company"):
		data["total"] = data[filters.company]
	else:
		data["total"] = sum(own_amounts.values())

	return data


def get_period_dates(fiscal_year, filters):
	if filters.filter_based_on == "Date Range":
		return filters.period_start_date, filters.period_end_date

	return fiscal_year.year_start_date, fiscal_year.year_end_date


def get_company_account_type_amount(company, filters):
	amount = get_account_type_based_gl_data(company, filters)
	if filters.account_type == "Depreciation":
		amount *= -1

	return amount


def get_column_amount(company, companies, own_amounts, filters):
	"""Amount for a company column, including its subsidiaries when accumulating into group companies."""
	if not filters.get("accumulated_in_group_company"):
		return own_amounts[company]

	amount = sum(
		convert_to_column_currency(own_amounts[subsidiary], subsidiary, company, filters)
		for subsidiary in companies[company]
	)
	return flt(amount, 3)


def convert_to_column_currency(amount, company, column_company, filters):
	column_currency = erpnext.get_company_currency(column_company)
	company_currency = erpnext.get_company_currency(company)

	if filters.get("presentation_currency") or column_currency == company_currency:
		return amount

	return convert(amount, column_currency, company_currency, filters.end_date)


def get_company_columns(companies, filters):
	company_columns = []
	for company in companies:
		apply_currency_formatter = 1 if not filters.presentation_currency else 0
		currency = filters.presentation_currency
		if not currency:
			currency = erpnext.get_company_currency(company)

		company_columns.append(
			{
				"fieldname": company,
				"label": f"{company} ({currency})",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 150,
				"apply_currency_formatter": apply_currency_formatter,
				"company_name": company,
			}
		)

	return company_columns


def get_columns(company_columns):
	columns = [
		{
			"fieldname": "account",
			"label": _("Account"),
			"fieldtype": "Link",
			"options": "Account",
			"width": 300,
		},
		{
			"fieldname": "currency",
			"label": _("Currency"),
			"fieldtype": "Link",
			"options": "Currency",
			"hidden": 1,
		},
	]

	columns.extend(company_columns)

	return columns


def get_data(
	companies,
	root_type,
	balance_must_be,
	fiscal_year,
	filters=None,
	ignore_closing_entries=False,
	translator=None,
):
	accounts, accounts_by_name, parent_children_map = get_account_heads(root_type, companies, filters)

	if not accounts:
		return []

	company_currency = get_company_currency(filters)

	if filters.filter_based_on == "Fiscal Year":
		start_date = fiscal_year.year_start_date if filters.report != "Balance Sheet" else None
		end_date = fiscal_year.year_end_date
	else:
		start_date = filters.period_start_date if filters.report != "Balance Sheet" else None
		end_date = filters.period_end_date

	filters.end_date = end_date

	gl_entries_by_account = {}
	for root in frappe.get_all(
		"Account",
		filters={"root_type": root_type, "parent_account": ["is", "not set"]},
		fields=["lft", "rgt"],
	):
		set_gl_entries_by_account(
			start_date,
			end_date,
			root.lft,
			root.rgt,
			filters,
			gl_entries_by_account,
			accounts_by_name,
			accounts,
			ignore_closing_entries=ignore_closing_entries,
			root_type=root_type,
		)

	translator = translator or CurrencyTranslator(companies, filters, fiscal_year)
	calculate_values(accounts_by_name, gl_entries_by_account, translator)
	if root_type == "Equity":
		add_translation_reserve_account(accounts, translator)

	accumulate_values_into_parents(accounts, accounts_by_name, companies)

	out = prepare_data(accounts, start_date, end_date, balance_must_be, companies, company_currency, filters)

	out = filter_out_zero_value_rows(
		out, parent_children_map, show_zero_values=filters.get("show_zero_values")
	)

	if out:
		add_total_row(out, root_type, balance_must_be, companies, company_currency)

	return out


def get_company_currency(filters=None):
	return filters.get("presentation_currency") or frappe.get_cached_value(
		"Company", filters.company, "default_currency"
	)


def calculate_values(accounts_by_name, gl_entries_by_account, translator):
	for entries in gl_entries_by_account.values():
		for entry in entries:
			if entry.account_number:
				account_name = entry.account_number + " - " + entry.account_name
			else:
				account_name = entry.account_name

			if account := accounts_by_name.get(account_name):
				add_entry_to_columns(account, entry, translator)


def add_entry_to_columns(account, entry, translator):
	amount = 0.0
	is_opening = translator.is_opening(entry)
	for company in translator.get_column_companies(entry):
		amount = translator.translate(entry, company)
		account[company] = account.get(company, 0.0) + amount

		if is_opening:
			account["company_wise_opening_bal"][company] += amount

	if is_opening:
		account["opening_balance"] = account.get("opening_balance", 0.0) + amount


class CurrencyTranslator:
	"""Translates each company's amounts into the currency of a report column.

	Income, expense and equity keep the rate of the transaction (the amounts in reporting currency on
	the GL Entry), other balances take the closing rate. The difference is the column's foreign
	currency translation reserve, as in Consolidated Trial Balance."""

	def __init__(self, companies: dict, filters: dict, fiscal_year: dict):
		self.companies = companies
		self.filters = filters
		self.start_date, self.end_date = get_period_dates(fiscal_year, filters)
		self.start_date = getdate(self.start_date)
		self.reserve = defaultdict(float)
		self.opening_reserve = defaultdict(float)

	def get_column_companies(self, entry) -> list[str]:
		return [company for company in self.companies if entry.company in self.get_column_scope(company)]

	def get_column_scope(self, company: str) -> list[str]:
		if self.filters.get("accumulated_in_group_company"):
			return self.companies[company]
		return [company]

	def get_target_currency(self, company: str) -> str:
		return self.filters.get("presentation_currency") or erpnext.get_company_currency(company)

	def is_opening(self, entry) -> bool:
		return entry.posting_date < self.start_date

	def translate(self, entry, company: str) -> float:
		"""Debit minus credit of `entry` in the currency of the `company` column."""
		amount = flt(entry.debit) - flt(entry.credit)
		currency = self.get_target_currency(company)
		if entry.currency == currency:
			return amount

		closing_amount = convert(amount, currency, entry.currency, self.end_date)
		if not uses_transaction_rate(entry):
			return closing_amount

		translated_amount = self.get_transaction_rate_amount(entry, currency, amount)
		self.reserve[company] += closing_amount - translated_amount
		if self.is_opening(entry):
			self.opening_reserve[company] += closing_amount - translated_amount

		return translated_amount

	def get_transaction_rate_amount(self, entry, currency: str, amount: float) -> float:
		"""Entries posted before reporting amounts existed are converted at their posting date."""
		reporting_currency = frappe.get_cached_value("Company", entry.company, "reporting_currency")
		if reporting_currency == currency and (
			entry.debit_in_reporting_currency or entry.credit_in_reporting_currency
		):
			return flt(entry.debit_in_reporting_currency) - flt(entry.credit_in_reporting_currency)

		return amount * get_rate_as_at(entry.posting_date, entry.currency, currency)

	def add_profit_and_loss_difference(self):
		"""Balance Sheet does not fetch income and expense, but their translation difference is in the reserve."""
		for company in self.get_foreign_companies():
			from_date = self.get_unclosed_from_date(company)
			for entry in get_profit_and_loss_totals(company, from_date, self.end_date, self.filters):
				for column in self.get_column_companies(entry):
					self.translate(entry, column)

	def get_unclosed_from_date(self, company: str):
		"""Closed income and expense are in retained earnings, which is translated as equity."""
		closed_until = frappe.get_all(
			"Period Closing Voucher",
			filters={
				"company": company,
				"docstatus": 1,
				"gle_processing_status": "Completed",
				"period_end_date": ("<=", self.end_date),
			},
			order_by="period_end_date desc",
			limit=1,
			pluck="period_end_date",
		)
		if closed_until and getdate(closed_until[0]) >= self.start_date:
			return add_days(closed_until[0], 1)

		return self.start_date

	def get_foreign_companies(self) -> set[str]:
		return {
			company
			for column in self.companies
			for company in self.get_column_scope(column)
			if erpnext.get_company_currency(company) != self.get_target_currency(column)
		}


def uses_transaction_rate(entry) -> bool:
	return entry.report_type == "Profit and Loss" or "Equity" in (entry.root_type, entry.account_type)


def get_profit_and_loss_totals(company: str, from_date, to_date, filters: dict) -> list[dict]:
	"""Income and expense of `company` in the period, per posting date and presence of reporting amounts."""
	gle = frappe.qb.DocType("GL Entry")
	account = frappe.qb.DocType("Account")
	has_reporting_amounts = (
		Case()
		.when((gle.debit_in_reporting_currency != 0) | (gle.credit_in_reporting_currency != 0), 1)
		.else_(0)
	)
	entries = (
		frappe.qb.from_(gle)
		.inner_join(account)
		.on(account.name == gle.account)
		.select(
			gle.company,
			gle.posting_date,
			Sum(gle.debit).as_("debit"),
			Sum(gle.credit).as_("credit"),
			Sum(gle.debit_in_reporting_currency).as_("debit_in_reporting_currency"),
			Sum(gle.credit_in_reporting_currency).as_("credit_in_reporting_currency"),
		)
		.where(
			(gle.company == company)
			& (gle.is_cancelled == 0)
			& (gle.posting_date <= to_date)
			& (account.report_type == "Profit and Loss")
		)
		.where(
			Criterion.all(get_additional_conditions(from_date, False, filters, frappe._dict(name=company)))
		)
		.groupby(gle.company, gle.posting_date, has_reporting_amounts)
		.run(as_dict=True)
	)

	currency = erpnext.get_company_currency(company)
	for entry in entries:
		entry.update(currency=currency, report_type="Profit and Loss")

	return entries


def add_translation_reserve_account(accounts, translator):
	"""Show the reserve as the first child of the equity root, like Consolidated Trial Balance."""
	if not any(flt(amount, 3) for amount in translator.reserve.values()):
		return

	root = accounts[0]
	label = _("Foreign Currency Translation Reserve")
	reserve = frappe._dict(
		translator.reserve,
		name=label,
		account_name=label,
		account_key=label,
		parent_account=root.name,
		parent_account_name=root.account_key,
		root_type=root.root_type,
		indent=root.indent + 1,
		is_group=0,
		company_wise_opening_bal=defaultdict(float, translator.opening_reserve),
	)
	accounts.insert(1, reserve)


def accumulate_values_into_parents(accounts, accounts_by_name, companies):
	"""accumulate children's values in parent accounts"""
	for d in reversed(accounts):
		if d.parent_account:
			account = d.parent_account_name

			for company in companies:
				accounts_by_name[account][company] = accounts_by_name[account].get(company, 0.0) + d.get(
					company, 0.0
				)

				accounts_by_name[account]["company_wise_opening_bal"][company] += d.get(
					"company_wise_opening_bal", {}
				).get(company, 0.0)

			accounts_by_name[account]["opening_balance"] = accounts_by_name[account].get(
				"opening_balance", 0.0
			) + d.get("opening_balance", 0.0)


def get_account_heads(root_type, companies, filters):
	accounts = get_accounts(root_type, companies)

	if not accounts:
		return None, None, None

	accounts = update_parent_account_names(accounts)

	accounts, accounts_by_name, parent_children_map = filter_accounts(accounts)

	return accounts, accounts_by_name, parent_children_map


def update_parent_account_names(accounts):
	"""Update parent_account_name in accounts list.

	parent_name is `name` of parent account which could have other prefix
	of account_number and suffix of company abbr. This function adds key called
	`parent_account_name` which does not have such prefix/suffix.
	"""
	name_to_account_map = {}

	for d in accounts:
		if d.account_number:
			account_key = d.account_number + " - " + d.account_name
		else:
			account_key = d.account_name

		d.account_key = account_key

		name_to_account_map[d.name] = account_key

	for account in accounts:
		if account.parent_account:
			account["parent_account_name"] = name_to_account_map.get(account.parent_account)

	return accounts


def get_companies(filters):
	companies = {}
	all_companies = get_subsidiary_companies(filters.get("company"))
	companies.setdefault(filters.get("company"), all_companies)

	for d in all_companies:
		if d not in companies:
			subsidiary_companies = get_subsidiary_companies(d)
			companies.setdefault(d, subsidiary_companies)

	return all_companies, companies


def get_subsidiary_companies(company):
	lft, rgt = frappe.get_cached_value("Company", company, ["lft", "rgt"])

	return frappe.get_all(
		"Company",
		filters={"lft": [">=", lft], "rgt": ["<=", rgt]},
		pluck="name",
		order_by="lft, rgt",
	)


def get_accounts(root_type, companies):
	accounts = []

	for company in companies:
		accounts.extend(
			frappe.get_all(
				"Account",
				fields=[
					"name",
					"is_group",
					"company",
					"parent_account",
					"lft",
					"rgt",
					"root_type",
					"report_type",
					"account_name",
					"account_number",
				],
				filters={"company": company, "root_type": root_type},
			)
		)

	return accounts


def prepare_data(accounts, start_date, end_date, balance_must_be, companies, company_currency, filters):
	data = []

	for d in accounts:
		# add to output
		has_value = False
		total = 0
		row = frappe._dict(
			{
				"account_name": (
					f"{_(d.account_number)} - {_(d.account_name)}" if d.account_number else _(d.account_name)
				),
				"account": _(d.name),
				"parent_account": _(d.parent_account),
				"indent": flt(d.indent),
				"year_start_date": start_date,
				"root_type": d.root_type,
				"year_end_date": end_date,
				"currency": filters.presentation_currency,
				"company_wise_opening_bal": d.company_wise_opening_bal,
				"opening_balance": d.get("opening_balance", 0.0) * (1 if balance_must_be == "Debit" else -1),
			}
		)

		for company in companies:
			if d.get(company) and balance_must_be == "Credit":
				# change sign based on Debit or Credit, since calculation is done using (debit - credit)
				d[company] *= -1

			row[company] = flt(d.get(company, 0.0), 3)

			if abs(row[company]) >= get_zero_cutoff(filters.presentation_currency):
				# ignore zero values
				has_value = True
				total += flt(row[company])

		row["has_value"] = has_value
		row["total"] = total
		set_group_company_total(row, filters)

		data.append(row)

	return data


def set_group_company_total(row, filters):
	"""The group company column already includes its subsidiaries; summing every column double-counts."""
	if row and filters.get("accumulated_in_group_company"):
		row["total"] = flt(row.get(filters.company, 0.0), 3)


def set_gl_entries_by_account(
	from_date,
	to_date,
	root_lft,
	root_rgt,
	filters,
	gl_entries_by_account,
	accounts_by_name,
	accounts,
	ignore_closing_entries=False,
	root_type=None,
):
	"""Returns a dict like { "account": [gl entries], ... }"""

	company_lft, company_rgt = frappe.get_cached_value("Company", filters.get("company"), ["lft", "rgt"])

	companies = frappe.get_all(
		"Company",
		filters={"lft": [">=", company_lft], "rgt": ["<=", company_rgt]},
		fields=["name", "default_currency"],
	)

	currency_info = frappe._dict(
		{"report_date": to_date, "presentation_currency": filters.get("presentation_currency")}
	)

	for d in companies:
		gle = frappe.qb.DocType("GL Entry")
		account = frappe.qb.DocType("Account")
		query = (
			frappe.qb.from_(gle)
			.inner_join(account)
			.on(account.name == gle.account)
			.select(
				gle.posting_date,
				gle.account,
				gle.debit,
				gle.credit,
				gle.is_opening,
				gle.company,
				gle.fiscal_year,
				gle.debit_in_account_currency,
				gle.credit_in_account_currency,
				gle.account_currency,
				gle.debit_in_reporting_currency,
				gle.credit_in_reporting_currency,
				account.account_name,
				account.account_number,
				account.root_type,
				account.report_type,
				account.account_type,
			)
			.where(
				(gle.company == d.name)
				& (gle.is_cancelled == 0)
				& (gle.posting_date <= to_date)
				& (account.lft >= root_lft)
				& (account.rgt <= root_rgt)
			)
			.orderby(gle.account, gle.posting_date)
		)

		if root_type:
			query = query.where(account.root_type == root_type)
		additional_conditions = get_additional_conditions(from_date, ignore_closing_entries, filters, d)
		if additional_conditions:
			query = query.where(Criterion.all(additional_conditions))
		gl_entries = query.run(as_dict=True)
		for entry in gl_entries:
			entry.currency = d.default_currency

		if (
			filters
			and filters.get("presentation_currency")
			and filters.get("presentation_currency") != d.default_currency
		):
			currency_info["company"] = d.name
			currency_info["company_currency"] = d.default_currency
			convert_closing_rate_entries(gl_entries, currency_info)

		for entry in gl_entries:
			if entry.account_number:
				account_name = entry.account_number + " - " + entry.account_name
			else:
				account_name = entry.account_name

			validate_entries(account_name, entry, accounts_by_name, accounts)
			gl_entries_by_account.setdefault(account_name, []).append(entry)

	return gl_entries_by_account


def convert_closing_rate_entries(gl_entries, currency_info):
	"""Convert balances at the closing rate; `CurrencyTranslator` handles the rest at the transaction rate."""
	entries = [entry for entry in gl_entries if not uses_transaction_rate(entry)]
	convert_to_presentation_currency(entries, currency_info)
	for entry in entries:
		entry.currency = currency_info.presentation_currency


def get_account_details(account):
	return frappe.get_cached_value(
		"Account",
		account,
		[
			"name",
			"report_type",
			"root_type",
			"company",
			"is_group",
			"account_name",
			"account_number",
			"parent_account",
			"lft",
			"rgt",
		],
		as_dict=1,
	)


def validate_entries(key, entry, accounts_by_name, accounts):
	# If an account present in the child company and not in the parent company
	if key not in accounts_by_name:
		args = get_account_details(entry.account)

		if args.parent_account:
			parent_args = get_account_details(args.parent_account)

			args.update(
				{
					"lft": parent_args.lft + 1,
					"rgt": parent_args.rgt - 1,
					"indent": 3,
					"root_type": parent_args.root_type,
					"report_type": parent_args.report_type,
					"parent_account_name": parent_args.account_name,
					"company_wise_opening_bal": defaultdict(float),
				}
			)

		accounts_by_name.setdefault(key, args)

		idx = len(accounts)
		# To identify parent account index
		for index, row in enumerate(accounts):
			if row.parent_account_name == args.parent_account_name:
				idx = index
				break

		accounts.insert(idx + 1, args)


def get_additional_conditions(from_date, ignore_closing_entries, filters, d):
	gle = frappe.qb.DocType("GL Entry")
	additional_conditions = []

	if ignore_closing_entries:
		additional_conditions.append(gle.voucher_type != "Period Closing Voucher")

	if from_date:
		additional_conditions.append(gle.posting_date >= from_date)

	finance_books = []
	finance_books.append("")
	if filter_fb := filters.get("finance_book"):
		finance_books.append(filter_fb)

	if filters.get("include_default_book_entries"):
		if company_fb := frappe.get_cached_value("Company", d.name, "default_finance_book"):
			finance_books.append(company_fb)

		additional_conditions.append((gle.finance_book.isin(finance_books)) | gle.finance_book.isnull())
	else:
		additional_conditions.append((gle.finance_book.isin(finance_books)) | gle.finance_book.isnull())

	return additional_conditions


def add_total_row(out, root_type, balance_must_be, companies, company_currency):
	total_row = {
		"account_name": "'" + _("Total {0} ({1})").format(_(root_type), _(balance_must_be)) + "'",
		"account": "'" + _("Total {0} ({1})").format(_(root_type), _(balance_must_be)) + "'",
		"currency": company_currency,
	}

	for row in out:
		if not row.get("parent_account"):
			for company in companies:
				total_row.setdefault(company, 0.0)
				total_row[company] += row.get(company, 0.0)

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
	added_accounts = []

	for d in accounts:
		if d.account_key in added_accounts:
			continue

		added_accounts.append(d.account_key)
		d["company_wise_opening_bal"] = defaultdict(float)
		accounts_by_name[d.account_key] = d

		parent_children_map.setdefault(d.parent_account_name or None, []).append(d)

	filtered_accounts = []

	def add_to_list(parent, level):
		if level < depth:
			children = parent_children_map.get(parent) or []
			sort_accounts(children, is_root=True if parent is None else False)

			for child in children:
				child.indent = level
				filtered_accounts.append(child)
				add_to_list(child.account_key, level + 1)

	add_to_list(None, 0)

	return filtered_accounts, accounts_by_name, parent_children_map
