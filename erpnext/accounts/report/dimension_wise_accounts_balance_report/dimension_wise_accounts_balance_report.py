# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import cstr, flt

import erpnext
from erpnext.accounts.report.financial_statements import (
	filter_accounts,
	filter_out_zero_value_rows,
)
from erpnext.accounts.report.trial_balance.trial_balance import validate_filters
from erpnext.accounts.utils import get_zero_cutoff


def execute(filters=None):
	validate_filters(filters)
	dimension_list = get_dimensions(filters)

	if not dimension_list:
		return [], []

	columns = get_columns(dimension_list)
	data = get_data(filters, dimension_list)

	return columns, data


def get_data(filters, dimension_list):
	company_currency = erpnext.get_company_currency(filters.company)

	acc = frappe.db.sql(
		"""
		select
			name, account_number, parent_account, lft, rgt, root_type,
			report_type, account_name, include_in_gross, account_type, is_group
		from
			`tabAccount`
		where
			company=%s
			order by lft""",
		(filters.company),
		as_dict=True,
	)

	if not acc:
		return None

	accounts, accounts_by_name, parent_children_map = filter_accounts(acc)

	min_lft, max_rgt = frappe.db.sql(
		"""select min(lft), max(rgt) from `tabAccount`
		where company=%s""",
		(filters.company),
	)[0]

	account = frappe.db.sql_list(
		"""select name from `tabAccount`
		where lft >= %s and rgt <= %s and company = %s""",
		(min_lft, max_rgt, filters.company),
	)

	gl_entries_by_account = {}
	set_gl_entries_by_account(dimension_list, filters, account, gl_entries_by_account)
	format_gl_entries(
		gl_entries_by_account, accounts_by_name, dimension_list, frappe.scrub(filters.get("dimension"))
	)
	accumulate_values_into_parents(accounts, accounts_by_name, dimension_list)
	out = prepare_data(accounts, filters, company_currency, dimension_list)
	out = filter_out_zero_value_rows(out, parent_children_map)

	return out


def set_gl_entries_by_account(dimension_list, filters, account, gl_entries_by_account):
	condition = get_condition(filters.get("dimension"))

	if account:
		condition += " and account in ({})".format(", ".join([frappe.db.escape(d) for d in account]))

	gl_filters = {
		"company": filters.get("company"),
		"from_date": filters.get("from_date"),
		"to_date": filters.get("to_date"),
		"finance_book": cstr(filters.get("finance_book")),
	}

	gl_filters["dimensions"] = tuple(set(dimension_list))

	if filters.get("include_default_book_entries"):
		gl_filters["company_fb"] = frappe.get_cached_value("Company", filters.company, "default_finance_book")

	gl_entries = frappe.db.sql(
		"""
		select
			posting_date, account, {dimension}, debit, credit, is_opening, fiscal_year,
			debit_in_account_currency, credit_in_account_currency, account_currency
		from
			`tabGL Entry`
		where
			company=%(company)s
		{condition}
		and posting_date >= %(from_date)s
		and posting_date <= %(to_date)s
		and is_cancelled = 0
		order by account, posting_date""".format(
			dimension=frappe.scrub(filters.get("dimension")), condition=condition
		),
		gl_filters,
		as_dict=True,
	)  # nosec

	for entry in gl_entries:
		gl_entries_by_account.setdefault(entry.account, []).append(entry)


def format_gl_entries(gl_entries_by_account, accounts_by_name, dimension_list, dimension_type):
	for entries in gl_entries_by_account.values():
		for entry in entries:
			d = accounts_by_name.get(entry.account)
			if not d:
				frappe.msgprint(
					_("Could not retrieve information for {0}.").format(entry.account),
					title="Error",
					raise_exception=1,
				)

			for dimension in dimension_list:
				if dimension == entry.get(dimension_type):
					d[frappe.scrub(dimension)] = (
						d.get(frappe.scrub(dimension), 0.0) + flt(entry.debit) - flt(entry.credit)
					)


def prepare_data(accounts, filters, company_currency, dimension_list):
	data = []

	for d in accounts:
		has_value = False
		total = 0
		row = {
			"account": d.name,
			"parent_account": d.parent_account,
			"indent": d.indent,
			"from_date": filters.from_date,
			"to_date": filters.to_date,
			"currency": company_currency,
			"account_name": (
				f"{d.account_number} - {d.account_name}" if d.account_number else d.account_name
			),
		}

		for dimension in dimension_list:
			row[frappe.scrub(dimension)] = flt(d.get(frappe.scrub(dimension), 0.0), 3)

			if abs(row[frappe.scrub(dimension)]) >= get_zero_cutoff(company_currency):
				# ignore zero values
				has_value = True
				total += flt(d.get(frappe.scrub(dimension), 0.0), 3)

		row["has_value"] = has_value
		row["total"] = total
		data.append(row)

	return data


def accumulate_values_into_parents(accounts, accounts_by_name, dimension_list):
	"""accumulate children's values in parent accounts"""
	for d in reversed(accounts):
		if d.parent_account:
			for dimension in dimension_list:
				accounts_by_name[d.parent_account][frappe.scrub(dimension)] = accounts_by_name[
					d.parent_account
				].get(frappe.scrub(dimension), 0.0) + d.get(frappe.scrub(dimension), 0.0)


def get_condition(dimension):
	conditions = []

	conditions.append(f"{frappe.scrub(dimension)} in %(dimensions)s")

	return " and {}".format(" and ".join(conditions)) if conditions else ""


def get_dimensions(filters):
	meta = frappe.get_meta(filters.get("dimension"), cached=False)
	query_filters = {}

	if meta.has_field("company"):
		query_filters = {"company": filters.get("company")}

	return frappe.get_all(filters.get("dimension"), filters=query_filters, pluck="name")


def get_columns(dimension_list):
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

	for dimension in dimension_list:
		columns.append(
			{
				"fieldname": frappe.scrub(dimension),
				"label": dimension,
				"fieldtype": "Currency",
				"options": "currency",
				"width": 150,
			}
		)

	columns.append(
		{
			"fieldname": "total",
			"label": _("Total"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 150,
		}
	)

	return columns
