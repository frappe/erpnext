# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.utils import add_days, cint, flt

from erpnext.accounts.doctype.financial_report_template.financial_report_engine import (
	FinancialReportEngine,
	get_xlsx_styles,  #! DO NOT REMOVE - hook for styling
)
from erpnext.accounts.report.financial_statements import (
	accumulate_values_into_parents,
	add_total_row,
	calculate_values,
	compute_growth_view_data,
	filter_accounts,
	filter_out_zero_value_rows,
	get_accounting_entries,
	get_accounts,
	get_appropriate_currency,
	get_columns,
	get_data,
	get_filtered_list_for_consolidated_report,
	get_period_list,
	prepare_data,
)


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

	filters.period_start_date = period_list[0]["year_start_date"]

	currency = filters.presentation_currency or frappe.get_cached_value(
		"Company", filters.company, "default_currency"
	)

	asset = get_data(
		filters.company,
		"Asset",
		"Debit",
		period_list,
		only_current_fiscal_year=False,
		filters=filters,
		accumulated_values=filters.accumulated_values,
	)

	liability = get_data(
		filters.company,
		"Liability",
		"Credit",
		period_list,
		only_current_fiscal_year=False,
		filters=filters,
		accumulated_values=filters.accumulated_values,
	)

	equity = get_data(
		filters.company,
		"Equity",
		"Credit",
		period_list,
		only_current_fiscal_year=False,
		filters=filters,
		accumulated_values=filters.accumulated_values,
	)

	provisional_profit_loss, total_credit = get_provisional_profit_loss(
		asset, liability, equity, period_list, filters.company, currency
	)

	message, opening_balance = check_opening_balance(asset, liability, equity)

	data = []
	data.extend(asset or [])
	data.extend(liability or [])
	data.extend(equity or [])
	if opening_balance and round(opening_balance, 2) != 0:
		unclosed = {
			"account_name": "'" + _("Unclosed Fiscal Years Profit / Loss (Credit)") + "'",
			"account": "'" + _("Unclosed Fiscal Years Profit / Loss (Credit)") + "'",
			"warn_if_negative": True,
			"currency": currency,
		}
		for period in period_list:
			unclosed[period.key] = opening_balance
			if provisional_profit_loss:
				provisional_profit_loss[period.key] = provisional_profit_loss[period.key] - opening_balance

		unclosed["total"] = opening_balance
		data.append(unclosed)

	if provisional_profit_loss:
		data.append(provisional_profit_loss)
	if total_credit:
		data.append(total_credit)

	columns = get_columns(
		filters.periodicity, period_list, filters.accumulated_values, company=filters.company
	)

	chart = get_chart_data(filters, period_list, asset, liability, equity, currency)

	report_summary, primitive_summary = get_report_summary(
		period_list, asset, liability, equity, provisional_profit_loss, currency, filters
	)

	if filters.get("selected_view") == "Growth":
		compute_growth_view_data(data, period_list)

	return columns, data, message, chart, report_summary, primitive_summary


def get_provisional_profit_loss(
	asset, liability, equity, period_list, company, currency=None, consolidated=False
):
	provisional_profit_loss = {}
	total_row = {}
	if asset:
		total = total_row_total = 0
		currency = currency or frappe.get_cached_value("Company", company, "default_currency")
		total_row = {
			"account_name": "'" + _("Total (Credit)") + "'",
			"account": "'" + _("Total (Credit)") + "'",
			"warn_if_negative": True,
			"currency": currency,
		}
		has_value = False

		for period in period_list:
			key = period if consolidated else period.key
			total_assets = flt(asset[-2].get(key))
			effective_liability = 0.00

			if liability and liability[-1] == {}:
				effective_liability += flt(liability[-2].get(key))
			if equity and equity[-1] == {}:
				effective_liability += flt(equity[-2].get(key))

			provisional_profit_loss[key] = total_assets - effective_liability
			total_row[key] = provisional_profit_loss[key] + effective_liability

			if provisional_profit_loss[key]:
				has_value = True

			total += flt(provisional_profit_loss[key])
			provisional_profit_loss["total"] = total

			total_row_total += flt(total_row[key])
			total_row["total"] = total_row_total

		if has_value:
			provisional_profit_loss.update(
				{
					"account_name": "'" + _("Provisional Profit / Loss (Credit)") + "'",
					"account": "'" + _("Provisional Profit / Loss (Credit)") + "'",
					"warn_if_negative": True,
					"currency": currency,
				}
			)

	return provisional_profit_loss, total_row


def check_opening_balance(asset, liability, equity):
	# Check if previous year balance sheet closed
	opening_balance = 0
	float_precision = cint(frappe.db.get_default("float_precision")) or 2
	if asset:
		opening_balance = flt(asset[-1].get("opening_balance", 0), float_precision)
	if liability:
		opening_balance -= flt(liability[-1].get("opening_balance", 0), float_precision)
	if equity:
		opening_balance -= flt(equity[-1].get("opening_balance", 0), float_precision)

	opening_balance = flt(opening_balance, float_precision)
	if opening_balance:
		return _("Previous Financial Year is not closed"), opening_balance
	return None, None


def get_report_summary(
	period_list,
	asset,
	liability,
	equity,
	provisional_profit_loss,
	currency,
	filters,
	consolidated=False,
):
	net_asset, net_liability, net_equity, net_provisional_profit_loss = 0.0, 0.0, 0.0, 0.0

	if filters.get("accumulated_values"):
		period_list = [period_list[-1]]

	# from consolidated financial statement
	if filters.get("accumulated_in_group_company"):
		period_list = get_filtered_list_for_consolidated_report(filters, period_list)

	for period in period_list:
		key = period if consolidated else period.key
		if asset:
			net_asset += asset[-2].get(key)
		if liability and liability[-1] == {}:
			net_liability += liability[-2].get(key)
		if equity and equity[-1] == {}:
			net_equity += equity[-2].get(key)
		if provisional_profit_loss:
			net_provisional_profit_loss += provisional_profit_loss.get(key)

	return [
		{"value": net_asset, "label": _("Total Asset"), "datatype": "Currency", "currency": currency},
		{
			"value": net_liability,
			"label": _("Total Liability"),
			"datatype": "Currency",
			"currency": currency,
		},
		{"value": net_equity, "label": _("Total Equity"), "datatype": "Currency", "currency": currency},
		{
			"value": net_provisional_profit_loss,
			"label": _("Provisional Profit / Loss (Credit)"),
			"indicator": "Green" if net_provisional_profit_loss > 0 else "Red",
			"datatype": "Currency",
			"currency": currency,
		},
	], (net_asset - net_liability + net_equity)


def get_chart_data(filters, chart_columns, asset, liability, equity, currency):
	labels = [col.get("label") for col in chart_columns]

	asset_data, liability_data, equity_data = [], [], []

	for col in chart_columns:
		key = col.get("key") or col.get("fieldname")
		if asset:
			asset_data.append(asset[-2].get(key))
		if liability:
			liability_data.append(liability[-2].get(key))
		if equity:
			equity_data.append(equity[-2].get(key))

	datasets = []
	if asset_data:
		datasets.append({"name": _("Assets"), "values": asset_data})
	if liability_data:
		datasets.append({"name": _("Liabilities"), "values": liability_data})
	if equity_data:
		datasets.append({"name": _("Equity"), "values": equity_data})

	chart = {"data": {"labels": labels, "datasets": datasets}}

	if not filters.accumulated_values:
		chart["type"] = "bar"
	else:
		chart["type"] = "line"

	chart["fieldtype"] = "Currency"
	chart["options"] = "currency"
	chart["currency"] = currency

	return chart


def execute_synced_report(filters):
	from frappe.database.duckdb.database import get_latest_sync

	if not (conn := get_latest_sync("GL Entry")):
		frappe.throw(_("Balance Sheet requires {0} to be synced to DuckDB").format(frappe.bold("GL Entry")))

	period_list = get_period_list(
		filters.from_fiscal_year,
		filters.to_fiscal_year,
		filters.period_start_date,
		filters.period_end_date,
		filters.filter_based_on,
		filters.periodicity,
		company=filters.company,
	)
	filters.period_start_date = period_list[0]["year_start_date"]

	currency = filters.presentation_currency or frappe.get_cached_value(
		"Company", filters.company, "default_currency"
	)

	asset = _get_data_duckdb(conn, filters, "Asset", "Debit", period_list)
	liability = _get_data_duckdb(conn, filters, "Liability", "Credit", period_list)
	equity = _get_data_duckdb(conn, filters, "Equity", "Credit", period_list)

	provisional_profit_loss, total_credit = get_provisional_profit_loss(
		asset, liability, equity, period_list, filters.company, currency
	)
	message, opening_balance = check_opening_balance(asset, liability, equity)

	data = []
	data.extend(asset or [])
	data.extend(liability or [])
	data.extend(equity or [])
	if opening_balance and round(opening_balance, 2) != 0:
		unclosed = {
			"account_name": "'" + _("Unclosed Fiscal Years Profit / Loss (Credit)") + "'",
			"account": "'" + _("Unclosed Fiscal Years Profit / Loss (Credit)") + "'",
			"warn_if_negative": True,
			"currency": currency,
		}
		for period in period_list:
			unclosed[period.key] = opening_balance
			if provisional_profit_loss:
				provisional_profit_loss[period.key] = provisional_profit_loss[period.key] - opening_balance
		unclosed["total"] = opening_balance
		data.append(unclosed)

	if provisional_profit_loss:
		data.append(provisional_profit_loss)
	if total_credit:
		data.append(total_credit)

	columns = get_columns(
		filters.periodicity, period_list, filters.accumulated_values, company=filters.company
	)
	chart = get_chart_data(filters, period_list, asset, liability, equity, currency)
	report_summary, primitive_summary = get_report_summary(
		period_list, asset, liability, equity, provisional_profit_loss, currency, filters
	)

	if filters.get("selected_view") == "Growth":
		compute_growth_view_data(data, period_list)

	return columns, data, message, chart, report_summary, primitive_summary


def _get_data_duckdb(conn, filters, root_type, balance_must_be, period_list):
	accounts = get_accounts(filters.company, root_type)
	if not accounts:
		return None

	accounts, accounts_by_name, parent_children_map = filter_accounts(accounts)
	company_currency = get_appropriate_currency(filters.company, filters)

	gl_entries_by_account = {}
	_load_gl_entries_duckdb(conn, filters, period_list, accounts, gl_entries_by_account, root_type)

	calculate_values(
		accounts_by_name,
		gl_entries_by_account,
		period_list,
		filters.accumulated_values,
		False,
	)
	accumulate_values_into_parents(accounts, accounts_by_name, period_list)

	out = prepare_data(
		accounts,
		balance_must_be,
		period_list,
		company_currency,
		accumulated_values=filters.accumulated_values,
	)
	out = filter_out_zero_value_rows(out, parent_children_map, filters.show_zero_values)

	if out:
		add_total_row(out, root_type, balance_must_be, period_list, company_currency)

	return out


def _load_gl_entries_duckdb(conn, filters, period_list, accounts, gl_entries_by_account, root_type):
	from erpnext.accounts.report.trial_balance.trial_balance import (
		_extra_gl_conditions,
		_fetch_gl_rows_duckdb,
	)
	from erpnext.accounts.report.utils import convert_to_presentation_currency, get_currency

	company = filters.company
	year_start_date = period_list[0]["year_start_date"]
	last_to_date = period_list[-1]["to_date"]
	ignore_is_opening = frappe.get_single_value("Accounts Settings", "ignore_is_opening_check_for_reporting")

	leaf_accounts = [acc.name for acc in accounts if not acc.is_group]
	if not leaf_accounts:
		return

	opening_from_date = None
	ignore_opening_entries = False

	ignore_closing_balances = frappe.get_single_value("Accounts Settings", "ignore_account_closing_balance")
	if not ignore_closing_balances:
		last_pcv_list = frappe.db.get_all(
			"Period Closing Voucher",
			filters={
				"docstatus": 1,
				"company": company,
				"period_end_date": ("<", filters.get("period_start_date") or year_start_date),
			},
			fields=["period_end_date", "name"],
			order_by="period_end_date desc",
			limit=1,
		)
		if last_pcv_list:
			last_pcv = last_pcv_list[0]
			pcv_entries = get_accounting_entries(
				"Account Closing Balance",
				None,
				last_to_date,
				filters,
				root_type=root_type,
				ignore_closing_entries=False,
				period_closing_voucher=last_pcv.name,
			)
			if filters.get("presentation_currency"):
				convert_to_presentation_currency(pcv_entries, get_currency(filters))
			for entry in pcv_entries:
				gl_entries_by_account.setdefault(entry.account, []).append(entry)
			opening_from_date = add_days(last_pcv.period_end_date, 1)
			ignore_opening_entries = True

	extra_cond, extra_params = _extra_gl_conditions(filters)
	account_placeholders = ", ".join(["?"] * len(leaf_accounts))
	base_conds = [
		"company = ?",
		"is_cancelled = 0",
		f"account IN ({account_placeholders})",
	]
	base_params = [company, *leaf_accounts]
	if ignore_opening_entries and not ignore_is_opening:
		base_conds.append("is_opening = 'No'")
	base_conds.extend(extra_cond)
	base_params.extend(extra_params)

	# Opening GL entries from DuckDB (entries before year_start_date)
	open_conds = [*base_conds, "posting_date < ?"]
	open_params = [*base_params, year_start_date]
	if opening_from_date:
		open_conds = [*open_conds, "posting_date >= ?"]
		open_params = [*open_params, opening_from_date]

	opening_entries = _fetch_gl_rows_duckdb(conn, open_conds, open_params)
	if filters.get("presentation_currency"):
		convert_to_presentation_currency(opening_entries, get_currency(filters))
	synthetic_open_date = add_days(year_start_date, -1)
	for entry in opening_entries:
		entry.posting_date = synthetic_open_date
		gl_entries_by_account.setdefault(entry.account, []).append(entry)

	# Period GL entries from DuckDB (one aggregated query per period)
	for period in period_list:
		period_conds = [*base_conds, "posting_date >= ?", "posting_date <= ?"]
		period_params = [*base_params, period.from_date, period.to_date]

		period_entries = _fetch_gl_rows_duckdb(conn, period_conds, period_params)
		if filters.get("presentation_currency"):
			convert_to_presentation_currency(period_entries, get_currency(filters))
		for entry in period_entries:
			entry.posting_date = period.to_date
			gl_entries_by_account.setdefault(entry.account, []).append(entry)
