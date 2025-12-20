# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from datetime import timedelta

import frappe
from frappe import _
from frappe.query_builder import DocType
from frappe.utils import cstr, flt
from pypika import Order

from erpnext.accounts.doctype.financial_report_template.financial_report_engine import (
	FinancialReportEngine,
)
from erpnext.accounts.report.financial_statements import (
	get_columns,
	get_cost_centers_with_children,
	get_data,
	get_filtered_list_for_consolidated_report,
	get_period_list,
	set_gl_entries_by_account,
)
from erpnext.accounts.report.profit_and_loss_statement.profit_and_loss_statement import (
	get_net_profit_loss,
)
from erpnext.accounts.utils import get_fiscal_year


def execute(filters=None):
	if filters and filters.report_template:
		return FinancialReportEngine().execute(filters)

	period_list = get_period_list(
		filters.from_fiscal_year,
		filters.to_fiscal_year,
		filters.period_start_date,
		filters.period_end_date,
		filters.filter_based_on,
		filters.periodicity,
		company=filters.company,
	)

	cash_flow_sections = get_cash_flow_accounts()

	# compute net profit / loss
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

	net_profit_loss = get_net_profit_loss(income, expense, period_list, filters.company)

	data = []
	summary_data = {}
	company_currency = frappe.get_cached_value("Company", filters.company, "default_currency")

	for cash_flow_section in cash_flow_sections:
		section_data = []
		data.append(
			{
				"section_name": "'" + cash_flow_section["section_header"] + "'",
				"parent_section": None,
				"indent": 0.0,
				"section": cash_flow_section["section_header"],
			}
		)

		if len(data) == 1:
			# add first net income in operations section
			if net_profit_loss:
				net_profit_loss.update(
					{
						"indent": 1,
						"parent_section": cash_flow_sections[0]["section_header"],
						"section": net_profit_loss["account"],
					}
				)
				data.append(net_profit_loss)
				section_data.append(net_profit_loss)

		for row in cash_flow_section["account_types"]:
			row_data = get_account_type_based_data(
				filters.company, row["account_type"], period_list, filters.accumulated_values, filters
			)
			accounts = frappe.get_all(
				"Account",
				filters={
					"account_type": row["account_type"],
					"is_group": 0,
				},
				pluck="name",
			)
			row_data.update(
				{
					"section_name": row["label"],
					"section": row["label"],
					"indent": 1,
					"accounts": accounts,
					"parent_section": cash_flow_section["section_header"],
					"currency": company_currency,
				}
			)
			data.append(row_data)
			section_data.append(row_data)

		add_total_row_account(
			data,
			section_data,
			cash_flow_section["section_footer"],
			period_list,
			company_currency,
			summary_data,
			filters,
		)

	net_change_in_cash = add_total_row_account(
		data, data, _("Net Change in Cash"), period_list, company_currency, summary_data, filters
	)

	if filters.show_opening_and_closing_balance:
		show_opening_and_closing_balance(data, period_list, company_currency, net_change_in_cash, filters)

	columns = get_columns(
		filters.periodicity,
		period_list,
		filters.accumulated_values,
		filters.company,
		True,
	)

	chart = get_chart_data(columns, data, company_currency)

	report_summary = get_report_summary(summary_data, company_currency)

	return columns, data, None, chart, report_summary


def get_cash_flow_accounts():
	operation_accounts = {
		"section_name": "Operations",
		"section_footer": _("Net Cash from Operations"),
		"section_header": _("Cash Flow from Operations"),
		"account_types": [
			{"account_type": "Depreciation", "label": _("Depreciation")},
			{"account_type": "Receivable", "label": _("Net Change in Accounts Receivable")},
			{"account_type": "Payable", "label": _("Net Change in Accounts Payable")},
			{"account_type": "Stock", "label": _("Net Change in Inventory")},
		],
	}

	investing_accounts = {
		"section_name": "Investing",
		"section_footer": _("Net Cash from Investing"),
		"section_header": _("Cash Flow from Investing"),
		"account_types": [{"account_type": "Fixed Asset", "label": _("Net Change in Fixed Asset")}],
	}

	financing_accounts = {
		"section_name": "Financing",
		"section_footer": _("Net Cash from Financing"),
		"section_header": _("Cash Flow from Financing"),
		"account_types": [{"account_type": "Equity", "label": _("Net Change in Equity")}],
	}

	# combine all cash flow accounts for iteration
	return [operation_accounts, investing_accounts, financing_accounts]


def get_account_type_based_data(company, account_type, period_list, accumulated_values, filters):
	data = {}
	total = 0
	for period in period_list:
		start_date = get_start_date(period, accumulated_values, company)
		filters.start_date = start_date
		filters.end_date = period["to_date"]
		filters.account_type = account_type

		amount = get_account_type_based_gl_data(company, filters)

		if amount and account_type == "Depreciation":
			amount *= -1

		total += amount
		data.setdefault(period["key"], amount)

	data["total"] = total
	return data


def get_account_type_based_gl_data(company, filters=None):
	cond = ""
	filters = frappe._dict(filters or {})

	if filters.include_default_book_entries:
		company_fb = frappe.get_cached_value("Company", company, "default_finance_book")
		cond = """ AND (finance_book in ({}, {}, '') OR finance_book IS NULL)
			""".format(
			frappe.db.escape(filters.finance_book),
			frappe.db.escape(company_fb),
		)
	else:
		cond = " AND (finance_book in (%s, '') OR finance_book IS NULL)" % (
			frappe.db.escape(cstr(filters.finance_book))
		)

	if filters.get("cost_center"):
		filters.cost_center = get_cost_centers_with_children(filters.cost_center)
		cond += " and cost_center in %(cost_center)s"

	gl_sum = frappe.db.sql_list(
		f"""
		select sum(credit) - sum(debit)
		from `tabGL Entry`
		where company=%(company)s and posting_date >= %(start_date)s and posting_date <= %(end_date)s
			and voucher_type != 'Period Closing Voucher'
			and account in ( SELECT name FROM tabAccount WHERE account_type = %(account_type)s) {cond}
	""",
		filters,
	)

	return gl_sum[0] if gl_sum and gl_sum[0] else 0


def get_start_date(period, accumulated_values, company):
	if not accumulated_values and period.get("from_date"):
		return period["from_date"]

	start_date = period["year_start_date"]
	if accumulated_values:
		start_date = get_fiscal_year(period.to_date, company=company)[1]

	return start_date


def add_total_row_account(out, data, label, period_list, currency, summary_data, filters, consolidated=False):
	total_row = {
		"section_name": "'" + _("{0}").format(label) + "'",
		"section": "'" + _("{0}").format(label) + "'",
		"currency": currency,
	}

	summary_data[label] = 0

	# from consolidated financial statement
	if filters.get("accumulated_in_group_company"):
		period_list = get_filtered_list_for_consolidated_report(filters, period_list)

	for row in data:
		if row.get("parent_section"):
			for period in period_list:
				key = period if consolidated else period["key"]
				total_row.setdefault(key, 0.0)
				total_row[key] += row.get(key, 0.0)
				summary_data[label] += row.get(key)

			total_row.setdefault("total", 0.0)
			total_row["total"] += row["total"]

	out.append(total_row)
	out.append({})

	return total_row


def show_opening_and_closing_balance(out, period_list, currency, net_change_in_cash, filters):
	opening_balance = {
		"section_name": "Opening",
		"section": "Opening",
		"currency": currency,
	}
	closing_balance = {
		"section_name": "Closing (Opening + Total)",
		"section": "Closing (Opening + Total)",
		"currency": currency,
	}

	opening_amount = get_opening_balance(filters.company, period_list, filters) or 0.0
	running_total = opening_amount

	for i, period in enumerate(period_list):
		key = period["key"]
		change = net_change_in_cash.get(key, 0.0)

		opening_balance[key] = opening_amount if i == 0 else running_total
		running_total += change
		closing_balance[key] = running_total

	opening_balance["total"] = opening_balance[period_list[0]["key"]]
	closing_balance["total"] = closing_balance[period_list[-1]["key"]]

	out.extend([opening_balance, net_change_in_cash, closing_balance, {}])


def get_opening_balance(company, period_list, filters):
	from copy import deepcopy

	cash_value = {}
	account_types = get_cash_flow_accounts()
	net_profit_loss = 0.0

	local_filters = deepcopy(filters)
	local_filters.start_date, local_filters.end_date = get_opening_range_using_fiscal_year(
		company, period_list
	)

	for section in account_types:
		section_name = section.get("section_name")
		cash_value.setdefault(section_name, 0.0)

		if section_name == "Operations":
			net_profit_loss += get_net_income(company, period_list, local_filters)

		for account in section.get("account_types", []):
			account_type = account.get("account_type")
			local_filters.account_type = account_type

			amount = get_account_type_based_gl_data(company, local_filters) or 0.0

			if account_type == "Depreciation":
				cash_value[section_name] += amount * -1
			else:
				cash_value[section_name] += amount

	return sum(cash_value.values()) + net_profit_loss


def get_net_income(company, period_list, filters):
	gl_entries_by_account_for_income, gl_entries_by_account_for_expense = {}, {}
	income, expense = 0.0, 0.0
	from_date, to_date = get_opening_range_using_fiscal_year(company, period_list)

	for root_type in ["Income", "Expense"]:
		for root in frappe.db.sql(
			"""select lft, rgt from tabAccount
				where root_type=%s and ifnull(parent_account, '') = ''""",
			root_type,
			as_dict=1,
		):
			set_gl_entries_by_account(
				company,
				from_date,
				to_date,
				filters,
				gl_entries_by_account_for_income
				if root_type == "Income"
				else gl_entries_by_account_for_expense,
				root.lft,
				root.rgt,
				root_type=root_type,
				ignore_closing_entries=True,
			)

	for entries in gl_entries_by_account_for_income.values():
		for entry in entries:
			if entry.posting_date <= to_date:
				amount = (entry.debit - entry.credit) * -1
				income = flt((income + amount), 2)

	for entries in gl_entries_by_account_for_expense.values():
		for entry in entries:
			if entry.posting_date <= to_date:
				amount = entry.debit - entry.credit
				expense = flt((expense + amount), 2)

	return income - expense


def get_opening_range_using_fiscal_year(company, period_list):
	first_from_date = period_list[0]["from_date"]
	previous_day = first_from_date - timedelta(days=1)

	# Get the earliest fiscal year for the company

	FiscalYear = DocType("Fiscal Year")
	FiscalYearCompany = DocType("Fiscal Year Company")

	earliest_fy = (
		frappe.qb.from_(FiscalYear)
		.join(FiscalYearCompany)
		.on(FiscalYearCompany.parent == FiscalYear.name)
		.select(FiscalYear.year_start_date)
		.where(FiscalYearCompany.company == company)
		.orderby(FiscalYear.year_start_date, order=Order.asc)
		.limit(1)
	).run(as_dict=True)

	if not earliest_fy:
		frappe.throw(_("Not able to find the earliest Fiscal Year for the given company."))

	company_start_date = earliest_fy[0]["year_start_date"]
	return company_start_date, previous_day


def get_report_summary(summary_data, currency):
	report_summary = []

	for label, value in summary_data.items():
		report_summary.append({"value": value, "label": label, "datatype": "Currency", "currency": currency})

	return report_summary


def get_chart_data(columns, data, currency):
	labels = [d.get("label") for d in columns[2:]]
	datasets = [
		{
			"name": section.get("section").replace("'", ""),
			"values": [section.get(d.get("fieldname")) for d in columns[2:]],
		}
		for section in data
		if section.get("parent_section") is None and section.get("currency")
	]
	datasets = datasets[:-2]

	chart = {"data": {"labels": labels, "datasets": datasets}, "type": "bar"}

	chart["fieldtype"] = "Currency"
	chart["options"] = "currency"
	chart["currency"] = currency

	return chart
