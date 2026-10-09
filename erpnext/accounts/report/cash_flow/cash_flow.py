# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.query_builder.functions import Sum
from frappe.utils import cstr, flt
from pypika.terms import Bracket, LiteralValue

import erpnext
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
	get_dimension_with_children,
)
from erpnext.accounts.doctype.financial_report_template.financial_report_engine import (
	FinancialReportEngine,
	get_xlsx_styles,  #! DO NOT REMOVE - hook for styling
)
from erpnext.accounts.report.financial_statements import (
	build_period_list,
	get_appropriate_currency,
	get_columns,
	get_cost_centers_with_children,
	get_data,
	get_filtered_list_for_consolidated_report,
	get_period_keys_for_total,
)
from erpnext.accounts.report.profit_and_loss_statement.profit_and_loss_statement import (
	get_net_profit_loss,
)
from erpnext.accounts.report.utils import convert, get_currency
from erpnext.accounts.utils import get_fiscal_year


def execute(filters=None):
	if filters and filters.report_template:
		return FinancialReportEngine().execute(filters)

	period_list = build_period_list(filters)

	if not period_list:
		return

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

	net_profit_loss = get_net_profit_loss(
		income,
		expense,
		period_list,
		filters.company,
		accumulated_values=bool(filters.accumulated_values),
	)
	if net_profit_loss:
		total_keys = get_total_keys(period_list, filters.accumulated_values, filters.company)
		net_profit_loss["total"] = sum(net_profit_loss[key] for key in total_keys)

	data = []
	summary_data = {}
	currency = get_appropriate_currency(filters.company, filters)

	for cash_flow_section in cash_flow_sections:
		section_data = []
		data.append(
			{
				"section_name": "'" + cash_flow_section["section_header"] + "'",
				"parent_section": None,
				"indent": 0.0,
				"section": cash_flow_section["section_header"],
				"currency": currency,
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
					"company": filters.company,
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
					"currency": currency,
				}
			)
			data.append(row_data)
			section_data.append(row_data)

		add_total_row_account(
			data,
			section_data,
			cash_flow_section["section_footer"],
			period_list,
			currency,
			summary_data,
			filters,
		)

	net_change_in_cash = add_total_row_account(
		data,
		data,
		_("Net Change in Cash"),
		period_list,
		currency,
		summary_data,
		filters,
		add_blank_row=False,
	)

	if filters.show_opening_and_closing_balance:
		show_opening_and_closing_balance(data, period_list, currency, net_change_in_cash, filters)

	columns = get_columns(
		filters.periodicity,
		period_list,
		filters.accumulated_values,
		filters.company,
		True,
	)

	chart = get_chart_data(period_list, data, currency)

	report_summary = get_report_summary(summary_data, currency)

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
	for period in period_list:
		start_date = get_start_date(period, accumulated_values, company)
		filters.start_date = start_date
		filters.end_date = period["to_date"]
		filters.account_type = account_type
		filters.dimension_field = period.get("dimension_field")
		filters.dimension_value = period.get("dimension_value")

		amount = get_account_type_based_gl_data(company, filters)

		if amount and account_type == "Depreciation":
			amount *= -1

		data.setdefault(period["key"], amount)

	data["total"] = sum(data[key] for key in get_total_keys(period_list, accumulated_values, company))
	return data


def get_total_keys(
	period_list: list[dict], accumulated_values: bool, company: str, consolidated: bool = False
) -> list[str]:
	"""Period keys whose values add up to the total.

	Accumulated values restart every fiscal year, so the last period of each fiscal year
	(per dimension when grouped) is taken."""
	if consolidated or not accumulated_values:
		return get_period_keys_for_total(period_list, accumulated_values, consolidated)

	last_keys = {}
	for period in period_list:
		fiscal_year = get_fiscal_year(period.to_date, company=company)[0]
		last_keys[(period.get("dimension_value"), fiscal_year)] = period.key
	return list(last_keys.values())


def get_account_type_based_gl_data(company, filters=None):
	filters = frappe._dict(filters or {})

	gl = frappe.qb.DocType("GL Entry")
	acc = frappe.qb.DocType("Account")

	query = (
		frappe.qb.from_(gl)
		.select(Sum(gl.credit) - Sum(gl.debit))
		.where(gl.company == company)
		.where(gl.posting_date >= filters.start_date)
		.where(gl.posting_date <= filters.end_date)
		.where(gl.voucher_type != "Period Closing Voucher")
		.where(
			gl.account.isin(
				frappe.qb.from_(acc)
				.select(acc.name)
				.where(acc.is_group == 0)
				.where(acc.company == company)
				.where(acc.account_type == filters.account_type)
			)
		)
	)

	if not frappe.get_single_value("Accounts Settings", "ignore_is_opening_check_for_reporting"):
		query = query.where(gl.is_opening != "Yes")

	query = apply_gl_filters(query, gl, company, filters)

	result = query.run()
	amount = flt(result[0][0]) if result and result[0][0] else 0

	company_currency = erpnext.get_company_currency(company)
	if amount and filters.presentation_currency and filters.presentation_currency != company_currency:
		report_date = get_currency(filters)["report_date"]
		amount = convert(amount, filters.presentation_currency, company_currency, report_date)

	return amount


def apply_gl_filters(query, gl, company, filters):
	"""Apply the report's finance book, cost center, project, dimension and permission filters."""
	# finance book
	if filters.include_default_book_entries:
		company_fb = frappe.get_cached_value("Company", company, "default_finance_book")
		query = query.where(
			(gl.finance_book.isin([cstr(filters.finance_book), cstr(company_fb), ""]))
			| (gl.finance_book.isnull())
		)
	else:
		query = query.where(
			(gl.finance_book.isin([cstr(filters.finance_book), ""])) | (gl.finance_book.isnull())
		)

	# cost center (with children)
	if filters.get("cost_center"):
		cost_centers = get_cost_centers_with_children(filters.cost_center)
		query = query.where(gl.cost_center.isin(cost_centers))

	# project
	if filters.get("project"):
		projects = filters.project
		if not isinstance(projects, list):
			projects = frappe.parse_json(projects)
		query = query.where(gl.project.isin(projects))

	# per-period group-by-dimension filter (always a single exact value)
	if filters.get("dimension_field") and filters.get("dimension_value"):
		query = query.where(gl[filters.dimension_field] == filters.dimension_value)

	# accounting dimension filters selected in the filter bar
	for dimension in get_accounting_dimensions(as_list=False):
		if filters.get(dimension.fieldname):
			values = filters[dimension.fieldname]
			if frappe.get_cached_value("DocType", dimension.document_type, "is_tree"):
				values = get_dimension_with_children(dimension.document_type, values)
			query = query.where(gl[dimension.fieldname].isin(values))

	# apply permission filters
	from frappe.desk.reportview import build_match_conditions

	if match_conditions := build_match_conditions("GL Entry"):
		query = query.where(Bracket(LiteralValue(match_conditions)))

	return query


def get_start_date(period, accumulated_values, company):
	if not accumulated_values and period.get("from_date"):
		return period["from_date"]

	start_date = period["year_start_date"]
	if accumulated_values:
		start_date = get_fiscal_year(period.to_date, company=company)[1]

	return start_date


def add_total_row_account(
	out,
	data,
	label,
	period_list,
	currency,
	summary_data,
	filters,
	consolidated=False,
	add_blank_row=True,
):
	name_key = "account" if consolidated else "section"
	parent_key = "parent_account" if consolidated else "parent_section"
	label_str = "'" + str(label) + "'"

	total_row = {
		f"{name_key}_name": label_str,
		name_key: label_str,
		"currency": currency,
	}

	# from consolidated financial statement
	if filters.get("accumulated_in_group_company"):
		period_list = get_filtered_list_for_consolidated_report(filters, period_list)

	for row in data:
		if row.get(parent_key):
			for period in period_list:
				key = period if consolidated else period["key"]
				total_row.setdefault(key, 0.0)
				total_row[key] += row.get(key, 0.0)

			total_row.setdefault("total", 0.0)
			total_row["total"] += row.get("total", 0.0)

	summary_keys = get_total_keys(
		period_list, filters.get("accumulated_values"), filters.company, consolidated
	)
	summary_data[label] = sum(flt(total_row.get(key)) for key in summary_keys)

	out.append(total_row)

	if add_blank_row:
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

	# one entry per cost center / dimension (just one entry if not grouped)
	openings, running_total = {}, {}

	for period in period_list:
		key = period["key"]
		dimension = period.get("dimension_value")

		# first column of this dimension: fetch its own opening cash
		if dimension not in openings:
			filters.dimension_field = period.get("dimension_field")
			filters.dimension_value = dimension
			openings[dimension] = get_opening_balance(filters.company, period_list, filters) or 0.0
			running_total[dimension] = openings[dimension]

		opening_balance[key] = running_total[dimension]
		running_total[dimension] += net_change_in_cash.get(key, 0.0)
		closing_balance[key] = running_total[dimension]

	opening_balance["total"] = sum(openings.values())
	closing_balance["total"] = sum(running_total.values())

	out.extend([opening_balance, net_change_in_cash, closing_balance, {}])


def get_opening_balance(company, period_list, filters):
	"""Balance of the Cash and Bank accounts before the first period, plus their opening entries."""
	gl = frappe.qb.DocType("GL Entry")
	account = frappe.qb.DocType("Account")

	cash_accounts = (
		frappe.qb.from_(account)
		.select(account.name)
		.where(account.company == company)
		.where(account.is_group == 0)
		.where(account.account_type.isin(["Cash", "Bank"]))
	)
	query = (
		frappe.qb.from_(gl)
		.select(Sum(gl.debit) - Sum(gl.credit))
		.where(gl.company == company)
		.where(gl.is_cancelled == 0)
		.where(gl.account.isin(cash_accounts))
	)
	before_first_period = gl.posting_date < period_list[0]["from_date"]
	if frappe.get_single_value("Accounts Settings", "ignore_is_opening_check_for_reporting"):
		query = query.where(before_first_period)
	else:
		# opening entries are left out of the movements, so they belong to the opening whatever their date
		query = query.where(before_first_period | (gl.is_opening == "Yes"))
	query = apply_gl_filters(query, gl, company, filters)

	result = query.run()
	return flt(result[0][0]) if result else 0.0


def get_report_summary(summary_data, currency):
	report_summary = []
	for label, value in summary_data.items():
		report_summary.append({"value": value, "label": label, "datatype": "Currency", "currency": currency})

	return report_summary


def get_chart_data(period_list, data, currency):
	labels = [period.get("label") for period in period_list]
	datasets = [
		{
			"name": section.get("section").replace("'", ""),
			"values": [section.get(period.get("key")) for period in period_list],
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
