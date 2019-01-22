# -*- coding: utf-8 -*-

# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import re
from past.builtins import cmp
import functools

import frappe, erpnext
from erpnext.accounts.report.utils import get_currency, convert_to_presentation_currency
from erpnext.accounts.utils import get_fiscal_year
from frappe import _
from frappe.utils import (flt, getdate, get_first_day, add_months, add_days, formatdate)

from six import itervalues

def get_period_list(from_fiscal_year, to_fiscal_year, periodicity, accumulated_values=False,
	company=None, reset_period_on_fy_change=True):
	"""Get a list of dict {"from_date": from_date, "to_date": to_date, "key": key, "label": label}
		Periodicity can be (Yearly, Quarterly, Monthly)"""

	fiscal_year = get_fiscal_year_data(from_fiscal_year, to_fiscal_year)
	validate_fiscal_year(fiscal_year, from_fiscal_year, to_fiscal_year)

	# start with first day, so as to avoid year to_dates like 2-April if ever they occur]
	year_start_date = getdate(fiscal_year.year_start_date)
	year_end_date = getdate(fiscal_year.year_end_date)

	months_to_add = {
		"Yearly": 12,
		"Half-Yearly": 6,
		"Quarterly": 3,
		"Monthly": 1
	}[periodicity]

	period_list = []

	start_date = year_start_date
	months = get_months(year_start_date, year_end_date)

	for i in range(months // months_to_add):
		period = frappe._dict({
			"from_date": start_date
		})

		to_date = add_months(start_date, months_to_add)
		start_date = to_date

		if to_date == get_first_day(to_date):
			# if to_date is the first day, get the last day of previous month
			to_date = add_days(to_date, -1)

		if to_date <= year_end_date:
			# the normal case
			period.to_date = to_date
		else:
			# if a fiscal year ends before a 12 month period
			period.to_date = year_end_date

		period.to_date_fiscal_year = get_fiscal_year(period.to_date, company=company)[0]
		period.from_date_fiscal_year_start_date = get_fiscal_year(period.from_date, company=company)[1]

		period_list.append(period)

		if period.to_date == year_end_date:
			break

	# common processing
	for opts in period_list:
		key = opts["to_date"].strftime("%b_%Y").lower()
		if periodicity == "Monthly" and not accumulated_values:
			label = formatdate(opts["to_date"], "MMM YYYY")
		else:
			if not accumulated_values:
				label = get_label(periodicity, opts["from_date"], opts["to_date"])
			else:
				if reset_period_on_fy_change:
					label = get_label(periodicity, opts.from_date_fiscal_year_start_date, opts["to_date"])
				else:
					label = get_label(periodicity, period_list[0].from_date, opts["to_date"])

		opts.update({
			"key": key.replace(" ", "_").replace("-", "_"),
			"label": label,
			"year_start_date": year_start_date,
			"year_end_date": year_end_date
		})

	return period_list


def get_fiscal_year_data(from_fiscal_year, to_fiscal_year):
	fiscal_year = frappe.db.sql("""select min(year_start_date) as year_start_date,
		max(year_end_date) as year_end_date from `tabFiscal Year` where
		name between %(from_fiscal_year)s and %(to_fiscal_year)s""",
		{'from_fiscal_year': from_fiscal_year, 'to_fiscal_year': to_fiscal_year}, as_dict=1)

	return fiscal_year[0] if fiscal_year else {}


def validate_fiscal_year(fiscal_year, from_fiscal_year, to_fiscal_year):
	if not fiscal_year.get('year_start_date') and not fiscal_year.get('year_end_date'):
		frappe.throw(_("End Year cannot be before Start Year"))


def get_months(start_date, end_date):
	diff = (12 * end_date.year + end_date.month) - (12 * start_date.year + start_date.month)
	return diff + 1


def get_label(periodicity, from_date, to_date):
	if periodicity == "Yearly":
		if formatdate(from_date, "YYYY") == formatdate(to_date, "YYYY"):
			label = formatdate(from_date, "YYYY")
		else:
			label = formatdate(from_date, "YYYY") + "-" + formatdate(to_date, "YYYY")
	else:
		label = formatdate(from_date, "MMM YY") + "-" + formatdate(to_date, "MMM YY")

	return label


def get_data(
		company, root_type, balance_must_be, period_list, filters=None,
		accumulated_values=1, only_current_fiscal_year=True, ignore_closing_entries=False,
		ignore_accumulated_values_for_fy=False):

	accounts = get_accounts(company, root_type)
	if not accounts:
		return None

	accounts, accounts_by_name, parent_children_map = filter_accounts(accounts)

	company_currency = get_appropriate_currency(company, filters)

	gl_entries_by_account = {}
	for root in frappe.db.sql("""select lft, rgt from tabAccount
			where root_type=%s and ifnull(parent_account, '') = ''""", root_type, as_dict=1):

		set_gl_entries_by_account(
			company,
			period_list[0]["year_start_date"] if only_current_fiscal_year else None,
			period_list[-1]["to_date"],
			root.lft, root.rgt, filters,
			gl_entries_by_account, ignore_closing_entries=ignore_closing_entries
		)

	calculate_values(
		accounts_by_name, gl_entries_by_account, period_list, accumulated_values, ignore_accumulated_values_for_fy)
	accumulate_values_into_parents(accounts, accounts_by_name, period_list, accumulated_values)
	out = prepare_data(accounts, balance_must_be, period_list, company_currency)
	out = filter_out_zero_value_rows(out, parent_children_map)

	if out:
		add_total_row(out, root_type, balance_must_be, period_list, company_currency)

	return out


def get_appropriate_currency(company, filters=None):
	if filters and filters.get("presentation_currency"):
		return filters["presentation_currency"]
	else:
		return frappe.get_cached_value('Company',  company,  "default_currency")


def calculate_values(
		accounts_by_name, gl_entries_by_account, period_list, accumulated_values, ignore_accumulated_values_for_fy):
	for entries in itervalues(gl_entries_by_account):
		for entry in entries:
			d = accounts_by_name.get(entry.account)
			if not d:
				frappe.msgprint(
					_("Could not retrieve information for {0}.".format(entry.account)), title="Error",
					raise_exception=1
				)
			for period in period_list:
				# check if posting date is within the period

				if entry.posting_date <= period.to_date:
					if (accumulated_values or entry.posting_date >= period.from_date) and \
						(not ignore_accumulated_values_for_fy or
							entry.fiscal_year == period.to_date_fiscal_year):
						d[period.key] = d.get(period.key, 0.0) + flt(entry.debit) - flt(entry.credit)

			if entry.posting_date < period_list[0].year_start_date:
				d["opening_balance"] = d.get("opening_balance", 0.0) + flt(entry.debit) - flt(entry.credit)


def accumulate_values_into_parents(accounts, accounts_by_name, period_list, accumulated_values):
	"""accumulate children's values in parent accounts"""
	for d in reversed(accounts):
		if d.parent_account:
			for period in period_list:
				accounts_by_name[d.parent_account][period.key] = \
					accounts_by_name[d.parent_account].get(period.key, 0.0) + d.get(period.key, 0.0)

			accounts_by_name[d.parent_account]["opening_balance"] = \
				accounts_by_name[d.parent_account].get("opening_balance", 0.0) + d.get("opening_balance", 0.0)


def prepare_data(accounts, balance_must_be, period_list, company_currency):
	data = []
	year_start_date = period_list[0]["year_start_date"].strftime("%Y-%m-%d")
	year_end_date = period_list[-1]["year_end_date"].strftime("%Y-%m-%d")

	for d in accounts:
		# add to output
		has_value = False
		total = 0
		row = frappe._dict({
			"account": _(d.name),
			"parent_account": _(d.parent_account) if d.parent_account else '',
			"indent": flt(d.indent),
			"year_start_date": year_start_date,
			"year_end_date": year_end_date,
			"currency": company_currency,
			"opening_balance": d.get("opening_balance", 0.0) * (1 if balance_must_be=="Debit" else -1),
			"account_name": ('%s - %s' %(_(d.account_number), _(d.account_name))
				if d.account_number else _(d.account_name))
		})
		for period in period_list:
			if d.get(period.key) and balance_must_be == "Credit":
				# change sign based on Debit or Credit, since calculation is done using (debit - credit)
				d[period.key] *= -1

			row[period.key] = flt(d.get(period.key, 0.0), 3)

			if abs(row[period.key]) >= 0.005:
				# ignore zero values
				has_value = True
				total += flt(row[period.key])

		row["has_value"] = has_value
		row["total"] = total
		data.append(row)

	return data


def filter_out_zero_value_rows(data, parent_children_map, show_zero_values=False):
	data_with_value = []
	for d in data:
		if show_zero_values or d.get("has_value"):
			data_with_value.append(d)
		else:
			# show group with zero balance, if there are balances against child
			children = [child.name for child in parent_children_map.get(d.get("account")) or []]
			if children:
				for row in data:
					if row.get("account") in children and row.get("has_value"):
						data_with_value.append(d)
						break

	return data_with_value


def add_total_row(out, root_type, balance_must_be, period_list, company_currency):
	total_row = {
		"account_name": "'" + _("Total {0} ({1})").format(_(root_type), _(balance_must_be)) + "'",
		"account": "'" + _("Total {0} ({1})").format(_(root_type), _(balance_must_be)) + "'",
		"currency": company_currency
	}

	for row in out:
		if not row.get("parent_account"):
			for period in period_list:
				total_row.setdefault(period.key, 0.0)
				total_row[period.key] += row.get(period.key, 0.0)
				row[period.key] = 0.0

			total_row.setdefault("total", 0.0)
			total_row["total"] += flt(row["total"])
			row["total"] = ""

	if "total" in total_row:
		out.append(total_row)

		# blank row after Total
		out.append({})


def get_accounts(company, root_type):
	return frappe.db.sql("""
		select name, account_number, parent_account, lft, rgt, root_type, report_type, account_name
		from `tabAccount`
		where company=%s and root_type=%s order by lft""", (company, root_type), as_dict=True)


def filter_accounts(accounts, depth=10):
	parent_children_map = {}
	accounts_by_name = {}
	for d in accounts:
		accounts_by_name[d.name] = d
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


def sort_accounts(accounts, is_root=False, key="name"):
	"""Sort root types as Asset, Liability, Equity, Income, Expense"""

	def compare_accounts(a, b):
		if is_root:
			if a.report_type != b.report_type and a.report_type == "Balance Sheet":
				return -1
			if a.root_type != b.root_type and a.root_type == "Asset":
				return -1
			if a.root_type == "Liability" and b.root_type == "Equity":
				return -1
			if a.root_type == "Income" and b.root_type == "Expense":
				return -1
		else:
			if re.split('\W+', a[key])[0].isdigit():
				# if chart of accounts is numbered, then sort by number
				return cmp(a[key], b[key])
		return 1

	accounts.sort(key = functools.cmp_to_key(compare_accounts))

def set_gl_entries_by_account(
		company, from_date, to_date, root_lft, root_rgt, filters, gl_entries_by_account, ignore_closing_entries=False):
	"""Returns a dict like { "account": [gl entries], ... }"""

	additional_conditions = get_additional_conditions(from_date, ignore_closing_entries, filters)

	accounts = frappe.db.sql_list("""select name from `tabAccount`
		where lft >= %s and rgt <= %s""", (root_lft, root_rgt))
	additional_conditions += " and account in ('{}')"\
		.format("', '".join([frappe.db.escape(d) for d in accounts]))

	gl_entries = frappe.db.sql("""select posting_date, account, debit, credit, is_opening, fiscal_year, debit_in_account_currency, credit_in_account_currency, account_currency from `tabGL Entry`
		where company=%(company)s
		{additional_conditions}
		and posting_date <= %(to_date)s
		order by account, posting_date""".format(additional_conditions=additional_conditions),
		{
			"company": company,
			"from_date": from_date,
			"to_date": to_date,
			"cost_center": filters.cost_center,
			"project": filters.project
		},
		as_dict=True)

	if filters and filters.get('presentation_currency'):
		convert_to_presentation_currency(gl_entries, get_currency(filters))

	for entry in gl_entries:
		gl_entries_by_account.setdefault(entry.account, []).append(entry)

	return gl_entries_by_account


def get_additional_conditions(from_date, ignore_closing_entries, filters):
	additional_conditions = []

	if ignore_closing_entries:
		additional_conditions.append("ifnull(voucher_type, '')!='Period Closing Voucher'")

	if from_date:
		additional_conditions.append("posting_date >= %(from_date)s")

	if filters:
		if filters.get("project"):
			if not isinstance(filters.get("project"), list):
				projects = frappe.safe_encode(filters.get("project"))
				filters.project = [d.strip() for d in projects.strip().split(',') if d]
			additional_conditions.append("project in %(project)s")

		if filters.get("cost_center"):
			filters.cost_center = get_cost_centers_with_children(filters.cost_center)
			additional_conditions.append("cost_center in %(cost_center)s")

		company_finance_book = erpnext.get_default_finance_book(filters.get("company"))

		if not filters.get('finance_book') or (filters.get('finance_book') == company_finance_book):
			additional_conditions.append("ifnull(finance_book, '') in ('%s', '')" %
				frappe.db.escape(company_finance_book))
		elif filters.get("finance_book"):
			additional_conditions.append("ifnull(finance_book, '') = '%s' " %
				frappe.db.escape(filters.get("finance_book")))

	return " and {}".format(" and ".join(additional_conditions)) if additional_conditions else ""

def get_cost_centers_with_children(cost_centers):
	if not isinstance(cost_centers, list):
		cost_centers = [d.strip() for d in cost_centers.strip().split(',') if d]

	all_cost_centers = []
	for d in cost_centers:
		lft, rgt = frappe.db.get_value("Cost Center", d, ["lft", "rgt"])
		children = frappe.get_all("Cost Center", filters={"lft": [">=", lft], "rgt": ["<=", rgt]})
		all_cost_centers += [c.name for c in children]

	return list(set(all_cost_centers))

def get_columns(periodicity, period_list, accumulated_values=1, company=None):
	columns = [{
		"fieldname": "account",
		"label": _("Account"),
		"fieldtype": "Link",
		"options": "Account",
		"width": 300
	}]
	if company:
		columns.append({
			"fieldname": "currency",
			"label": _("Currency"),
			"fieldtype": "Link",
			"options": "Currency",
			"hidden": 1
		})
	for period in period_list:
		columns.append({
			"fieldname": period.key,
			"label": period.label,
			"fieldtype": "Currency",
			"options": "currency",
			"width": 150
		})
	if periodicity!="Yearly":
		if not accumulated_values:
			columns.append({
				"fieldname": "total",
				"label": _("Total"),
				"fieldtype": "Currency",
				"width": 150
			})

	return columns
