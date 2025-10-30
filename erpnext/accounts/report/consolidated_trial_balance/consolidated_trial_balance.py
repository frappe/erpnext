# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, now_datetime, nowdate

import erpnext
from erpnext.accounts.doctype.account.account import get_root_company
from erpnext.accounts.report.financial_statements import (
	filter_accounts,
	filter_out_zero_value_rows,
	set_gl_entries_by_account,
)
from erpnext.accounts.report.trial_balance.trial_balance import (
	accumulate_values_into_parents,
	calculate_values,
	get_opening_balances,
	hide_group_accounts,
	prepare_opening_closing,
	value_fields,
)
from erpnext.accounts.report.trial_balance.trial_balance import (
	validate_filters as tb_validate_filters,
)
from erpnext.accounts.report.utils import get_rate_as_at
from erpnext.accounts.utils import get_zero_cutoff
from erpnext.setup.utils import get_exchange_rate


def execute(filters: dict | None = None):
	"""Return columns and data for the report.

	This is the main entry point for the report. It accepts the filters as a
	dictionary and should return columns and data. It is called by the framework
	every time the report is refreshed or a filter is updated.
	"""
	validate_filters(filters=filters)
	columns = get_columns()
	data = get_data(filters)

	return columns, data


def validate_filters(filters):
	validate_companies(filters)
	filters.show_net_values = True
	tb_validate_filters(filters)


def validate_companies(filters):
	if not filters.company:
		return

	root_company = get_root_company(filters.company[0])
	root_company = root_company[0] if root_company else filters.company[0]

	lft, rgt = frappe.db.get_value("Company", root_company, fieldname=["lft", "rgt"])

	company_subtree = frappe.db.get_all(
		"Company",
		{"lft": [">=", lft], "rgt": ["<=", rgt]},
		"name",
		order_by="lft",
		pluck="name",
	)

	for company in filters.company:
		if company not in company_subtree:
			frappe.throw(
				_("Consolidated Trial Balance can be generated for Companies having same root Company.")
			)

	sort_companies(filters)


def sort_companies(filters):
	companies = frappe.db.get_all(
		"Company", {"name": ["in", filters.company]}, "name", order_by="lft", pluck="name"
	)
	filters.company = companies


def get_data(filters) -> list[list]:
	"""Return data for the report.

	The report data is a list of rows, with each row being a list of cell values.
	"""
	data = []
	if filters.company:
		reporting_currency, ignore_reporting_currency = get_reporting_currency(filters)
	else:
		return data

	for company in filters.company:
		company_filter = frappe._dict(filters)
		company_filter.company = company

		tb_data = get_company_wise_tb_data(company_filter, reporting_currency, ignore_reporting_currency)
		consolidate_trial_balance_data(data, tb_data)

	for d in data:
		prepare_opening_closing(d)

	total_row = calculate_total_row(data, reporting_currency)

	data.extend([{}, total_row])

	if not filters.get("show_group_accounts"):
		data = hide_group_accounts(data)

	if filters.get("presentation_currency"):
		update_to_presentation_currency(
			data,
			reporting_currency,
			filters.get("presentation_currency"),
			filters.get("to_date"),
			ignore_reporting_currency,
		)

	return data


def get_company_wise_tb_data(filters, reporting_currency, ignore_reporting_currency):
	accounts = frappe.db.sql(
		"""select name, account_number, parent_account, account_name, root_type, report_type, account_type, is_group, lft, rgt

		from `tabAccount` where company=%s order by lft""",
		filters.company,
		as_dict=True,
	)

	ignore_is_opening = frappe.get_single_value("Accounts Settings", "ignore_is_opening_check_for_reporting")

	default_currency = erpnext.get_company_currency(filters.company)

	opening_exchange_rate = get_exchange_rate(
		default_currency,
		reporting_currency,
		filters.get("from_date"),
	)
	current_date = (
		filters.get("to_date") if getdate(filters.get("to_date")) <= now_datetime().date() else nowdate()
	)
	closing_exchange_rate = get_exchange_rate(
		default_currency,
		reporting_currency,
		current_date,
	)

	if not (opening_exchange_rate and closing_exchange_rate):
		frappe.throw(
			_(
				"Consolidated Trial balance could not be generated as Exchange Rate from {0} to {1} is not available for {2}.",
			).format(default_currency, reporting_currency, current_date)
		)

	if not accounts:
		return []

	accounts, accounts_by_name, parent_children_map = filter_accounts(accounts)

	gl_entries_by_account = {}

	opening_balances = get_opening_balances(
		filters,
		ignore_is_opening,
		exchange_rate=opening_exchange_rate,
		ignore_reporting_currency=ignore_reporting_currency,
	)

	set_gl_entries_by_account(
		filters.company,
		filters.from_date,
		filters.to_date,
		filters,
		gl_entries_by_account,
		root_lft=None,
		root_rgt=None,
		ignore_closing_entries=not flt(filters.with_period_closing_entry_for_current_period),
		ignore_opening_entries=True,
		group_by_account=True,
		ignore_reporting_currency=ignore_reporting_currency,
	)

	calculate_values(
		accounts,
		gl_entries_by_account,
		opening_balances,
		filters.get("show_net_values"),
		ignore_is_opening=ignore_is_opening,
		exchange_rate=closing_exchange_rate,
		ignore_reporting_currency=ignore_reporting_currency,
	)

	accumulate_values_into_parents(accounts, accounts_by_name)

	data = prepare_companywise_tb_data(accounts, filters, parent_children_map, reporting_currency)
	data = filter_out_zero_value_rows(
		data, parent_children_map, show_zero_values=filters.get("show_zero_values")
	)

	return data


def prepare_companywise_tb_data(accounts, filters, parent_children_map, reporting_currency):
	data = []

	for d in accounts:
		# Prepare opening closing for group account
		if parent_children_map.get(d.account) and filters.get("show_net_values"):
			prepare_opening_closing(d)

		has_value = False
		row = {
			"account": d.name,
			"parent_account": d.parent_account,
			"indent": d.indent,
			"from_date": filters.from_date,
			"to_date": filters.to_date,
			"currency": reporting_currency,
			"is_group_account": d.is_group,
			"acc_name": d.account_name,
			"acc_number": d.account_number,
			"account_name": (
				f"{d.account_number} - {d.account_name}" if d.account_number else d.account_name
			),
			"root_type": d.root_type,
			"account_type": d.account_type,
		}

		for key in value_fields:
			row[key] = flt(d.get(key, 0.0), 3)

			if abs(row[key]) >= get_zero_cutoff(reporting_currency):
				# ignore zero values
				has_value = True

		row["has_value"] = has_value
		data.append(row)

	return data


def calculate_total_row(data, reporting_currency):
	total_row = {
		"account": "'" + _("Total") + "'",
		"account_name": "'" + _("Total") + "'",
		"warn_if_negative": True,
		"opening_debit": 0.0,
		"opening_credit": 0.0,
		"debit": 0.0,
		"credit": 0.0,
		"closing_debit": 0.0,
		"closing_credit": 0.0,
		"parent_account": None,
		"indent": 0,
		"has_value": True,
		"currency": reporting_currency,
	}

	for d in data:
		if not d.get("parent_account"):
			for field in value_fields:
				total_row[field] += d[field]

	if data:
		calculate_foreign_currency_translation_reserve(total_row, data)

	return total_row


def calculate_foreign_currency_translation_reserve(total_row, data):
	opening_dr_cr_diff = total_row["opening_debit"] - total_row["opening_credit"]
	dr_cr_diff = total_row["debit"] - total_row["credit"]

	idx = get_fctr_root_row_index(data)

	fctr_row = {
		"account": _("Foreign Currency Translation Reserve"),
		"account_name": _("Foreign Currency Translation Reserve"),
		"warn_if_negative": True,
		"opening_debit": abs(opening_dr_cr_diff) if opening_dr_cr_diff < 0 else 0.0,
		"opening_credit": abs(opening_dr_cr_diff) if opening_dr_cr_diff > 0 else 0.0,
		"debit": abs(dr_cr_diff) if dr_cr_diff < 0 else 0.0,
		"credit": abs(dr_cr_diff) if dr_cr_diff > 0 else 0.0,
		"closing_debit": 0.0,
		"closing_credit": 0.0,
		"root_type": data[idx].get("root_type"),
		"account_type": "Equity",
		"parent_account": data[idx].get("account"),
		"indent": data[idx].get("indent") + 1,
		"has_value": True,
		"currency": total_row.get("currency"),
	}

	fctr_row["closing_debit"] = fctr_row["opening_debit"] + fctr_row["debit"]
	fctr_row["closing_credit"] = fctr_row["opening_credit"] + fctr_row["credit"]

	prepare_opening_closing(fctr_row)

	data.insert(idx + 1, fctr_row)

	for field in value_fields:
		total_row[field] += fctr_row[field]


def get_fctr_root_row_index(data):
	"""
	Returns: index, root_type, parent_account
	"""
	liabilities_idx, equity_idx, tmp_idx = -1, -1, 0
	for d in data:
		if liabilities_idx == -1 and d.get("root_type") == "Liability":
			liabilities_idx = tmp_idx

		if equity_idx == -1 and d.get("root_type") == "Equity":
			equity_idx = tmp_idx

		tmp_idx += 1

	if equity_idx == -1:
		return liabilities_idx

	return equity_idx


def consolidate_trial_balance_data(data, tb_data):
	if not data:
		data.extend(list(tb_data))
		return

	for entry in tb_data:
		if entry:
			consolidate_gle_data(data, entry, tb_data)


def get_reporting_currency(filters):
	reporting_currency = frappe.get_cached_value("Company", filters.company[0], "reporting_currency")
	default_currency = None
	for company in filters.company:
		company_default_currency = erpnext.get_company_currency(company)
		if not default_currency:
			default_currency = company_default_currency

		if company_default_currency != default_currency:
			return (reporting_currency, False)

	return (default_currency, True)


def consolidate_gle_data(data, entry, tb_data):
	entry_gle_exists = False
	for gle in data:
		if gle and gle["account_name"] == entry["account_name"]:
			entry_gle_exists = True
			gle["closing_credit"] += entry["closing_credit"]
			gle["closing_debit"] += entry["closing_debit"]
			gle["credit"] += entry["credit"]
			gle["debit"] += entry["debit"]
			gle["opening_credit"] += entry["opening_credit"]
			gle["opening_debit"] += entry["opening_debit"]
			gle["has_value"] = 1

	if not entry_gle_exists:
		entry_parent_account = next(
			(d for d in tb_data if d.get("account") == entry.get("parent_account")), None
		)
		parent_account_in_data = None
		if entry_parent_account:
			parent_account_in_data = next(
				(d for d in data if d and d.get("account_name") == entry_parent_account.get("account_name")),
				None,
			)
		if parent_account_in_data:
			entry["parent_account"] = parent_account_in_data.get("account")
			entry["indent"] = (parent_account_in_data.get("indent") or 0) + 1
			data.insert(data.index(parent_account_in_data) + 1, entry)
		else:
			entry["parent_account"] = None
			entry["indent"] = 0
			data.append(entry)


def update_to_presentation_currency(data, from_currency, to_currency, date, ignore_reporting_currency):
	if from_currency == to_currency:
		return

	exchange_rate = get_rate_as_at(date, from_currency, to_currency)

	for d in data:
		if not ignore_reporting_currency:
			for field in value_fields:
				if d.get(field):
					d[field] = d[field] * flt(exchange_rate)
		d.update(currency=to_currency)


def get_columns():
	return [
		{
			"fieldname": "account_name",
			"label": _("Account"),
			"fieldtype": "Data",
			"width": 300,
		},
		{
			"fieldname": "acc_name",
			"label": _("Account Name"),
			"fieldtype": "Data",
			"hidden": 1,
			"width": 250,
		},
		{
			"fieldname": "acc_number",
			"label": _("Account Number"),
			"fieldtype": "Data",
			"hidden": 1,
			"width": 120,
		},
		{
			"fieldname": "currency",
			"label": _("Currency"),
			"fieldtype": "Link",
			"options": "Currency",
			"hidden": 1,
		},
		{
			"fieldname": "opening_debit",
			"label": _("Opening (Dr)"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
		{
			"fieldname": "opening_credit",
			"label": _("Opening (Cr)"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
		{
			"fieldname": "debit",
			"label": _("Debit"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
		{
			"fieldname": "credit",
			"label": _("Credit"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
		{
			"fieldname": "closing_debit",
			"label": _("Closing (Dr)"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
		{
			"fieldname": "closing_credit",
			"label": _("Closing (Cr)"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
	]
