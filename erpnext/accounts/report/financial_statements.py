# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import copy
import functools
import math
import re

import frappe
from frappe import _
from frappe.query_builder.functions import Max, Min, Sum
from frappe.utils import add_days, add_months, cint, cstr, flt, formatdate, get_first_day, getdate
from pypika.terms import ExistsCriterion

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
	get_dimension_with_children,
)
from erpnext.accounts.report.utils import convert_to_presentation_currency, get_currency
from erpnext.accounts.utils import get_fiscal_year, get_zero_cutoff


def get_period_list(
	from_fiscal_year,
	to_fiscal_year,
	period_start_date,
	period_end_date,
	filter_based_on,
	periodicity,
	accumulated_values=False,
	company=None,
	reset_period_on_fy_change=True,
	ignore_fiscal_year=False,
):
	"""Get a list of dict {"from_date": from_date, "to_date": to_date, "key": key, "label": label}
	Periodicity can be (Yearly, Quarterly, Monthly)"""

	if filter_based_on == "Fiscal Year":
		fiscal_year = get_fiscal_year_data(from_fiscal_year, to_fiscal_year)
		validate_fiscal_year(fiscal_year, from_fiscal_year, to_fiscal_year)
		year_start_date = getdate(fiscal_year.year_start_date)
		year_end_date = getdate(fiscal_year.year_end_date)
	else:
		validate_dates(period_start_date, period_end_date)
		year_start_date = getdate(period_start_date)
		year_end_date = getdate(period_end_date)

	months_to_add = {"Yearly": 12, "Half-Yearly": 6, "Quarterly": 3, "Monthly": 1}[periodicity]

	period_list = []

	start_date = year_start_date
	months = get_months(year_start_date, year_end_date)

	for i in range(cint(math.ceil(months / months_to_add))):
		period = frappe._dict({"from_date": start_date})

		if i == 0 and filter_based_on == "Date Range":
			to_date = add_months(get_first_day(start_date), months_to_add)
		else:
			to_date = add_months(start_date, months_to_add)

		start_date = to_date

		# Subtract one day from to_date, as it may be first day in next fiscal year or month
		to_date = add_days(to_date, -1)

		if to_date <= year_end_date:
			# the normal case
			period.to_date = to_date
		else:
			# if a fiscal year ends before a 12 month period
			period.to_date = year_end_date

		if not ignore_fiscal_year:
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

		opts.update(
			{
				"key": key.replace(" ", "_").replace("-", "_"),
				"label": label,
				"year_start_date": year_start_date,
				"year_end_date": year_end_date,
			}
		)

	return period_list


def get_fiscal_year_data(from_fiscal_year, to_fiscal_year):
	from_year_start_date = frappe.get_cached_value("Fiscal Year", from_fiscal_year, "year_start_date")
	to_year_end_date = frappe.get_cached_value("Fiscal Year", to_fiscal_year, "year_end_date")

	fy = frappe.qb.DocType("Fiscal Year")

	query = (
		frappe.qb.from_(fy)
		.select(Min(fy.year_start_date).as_("year_start_date"), Max(fy.year_end_date).as_("year_end_date"))
		.where(fy.year_start_date >= from_year_start_date)
		.where(fy.year_end_date <= to_year_end_date)
	)

	fiscal_year = query.run(as_dict=True)
	return fiscal_year[0] if fiscal_year else {}


def validate_fiscal_year(fiscal_year, from_fiscal_year, to_fiscal_year):
	if not fiscal_year.get("year_start_date") or not fiscal_year.get("year_end_date"):
		frappe.throw(_("Start Year and End Year are mandatory"))

	if getdate(fiscal_year.get("year_end_date")) < getdate(fiscal_year.get("year_start_date")):
		frappe.throw(_("End Year cannot be before Start Year"))


def validate_dates(from_date, to_date):
	if not from_date or not to_date:
		frappe.throw(_("From Date and To Date are mandatory"))

	if to_date < from_date:
		frappe.throw(_("To Date cannot be less than From Date"))


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
	company,
	root_type,
	balance_must_be,
	period_list,
	filters=None,
	accumulated_values=1,
	only_current_fiscal_year=True,
	ignore_closing_entries=False,
	ignore_accumulated_values_for_fy=False,
	total=True,
):
	accounts = get_accounts(company, root_type)
	if not accounts:
		return None

	accounts, accounts_by_name, parent_children_map = filter_accounts(accounts)

	company_currency = get_appropriate_currency(company, filters)

	gl_entries_by_account = {}
	for root in frappe.db.sql(
		"""select lft, rgt from tabAccount
			where root_type=%s and ifnull(parent_account, '') = ''""",
		root_type,
		as_dict=1,
	):
		set_gl_entries_by_account(
			company,
			period_list[0]["year_start_date"] if only_current_fiscal_year else None,
			period_list[-1]["to_date"],
			filters,
			gl_entries_by_account,
			root.lft,
			root.rgt,
			root_type=root_type,
			ignore_closing_entries=ignore_closing_entries,
		)

	calculate_values(
		accounts_by_name,
		gl_entries_by_account,
		period_list,
		accumulated_values,
		ignore_accumulated_values_for_fy,
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

	if out and total:
		add_total_row(out, root_type, balance_must_be, period_list, company_currency)

	return out


def get_appropriate_currency(company, filters=None):
	if filters and filters.get("presentation_currency"):
		return filters["presentation_currency"]
	else:
		return frappe.get_cached_value("Company", company, "default_currency")


def calculate_values(
	accounts_by_name,
	gl_entries_by_account,
	period_list,
	accumulated_values,
	ignore_accumulated_values_for_fy,
):
	for entries in gl_entries_by_account.values():
		for entry in entries:
			d = accounts_by_name.get(entry.account)
			if not d:
				frappe.msgprint(
					_("Could not retrieve information for {0}.").format(entry.account),
					title="Error",
					raise_exception=1,
				)
			for period in period_list:
				# check if posting date is within the period

				if entry.posting_date <= period.to_date:
					if (accumulated_values or entry.posting_date >= period.from_date) and (
						not ignore_accumulated_values_for_fy
						or entry.fiscal_year == period.to_date_fiscal_year
					):
						d[period.key] = d.get(period.key, 0.0) + flt(entry.debit) - flt(entry.credit)

			if entry.posting_date < period_list[0].year_start_date:
				d["opening_balance"] = d.get("opening_balance", 0.0) + flt(entry.debit) - flt(entry.credit)


def accumulate_values_into_parents(accounts, accounts_by_name, period_list):
	"""accumulate children's values in parent accounts"""
	for d in reversed(accounts):
		if d.parent_account:
			for period in period_list:
				accounts_by_name[d.parent_account][period.key] = accounts_by_name[d.parent_account].get(
					period.key, 0.0
				) + d.get(period.key, 0.0)

			accounts_by_name[d.parent_account]["opening_balance"] = accounts_by_name[d.parent_account].get(
				"opening_balance", 0.0
			) + d.get("opening_balance", 0.0)


def prepare_data(accounts, balance_must_be, period_list, company_currency, accumulated_values):
	data = []
	year_start_date = period_list[0]["year_start_date"].strftime("%Y-%m-%d")
	year_end_date = period_list[-1]["year_end_date"].strftime("%Y-%m-%d")

	for d in accounts:
		# add to output
		has_value = False
		total = 0
		row = frappe._dict(
			{
				"account": _(d.name),
				"parent_account": _(d.parent_account) if d.parent_account else "",
				"indent": flt(d.indent),
				"year_start_date": year_start_date,
				"year_end_date": year_end_date,
				"currency": company_currency,
				"include_in_gross": d.include_in_gross,
				"account_type": d.account_type,
				"is_group": d.is_group,
				"opening_balance": d.get("opening_balance", 0.0) * (1 if balance_must_be == "Debit" else -1),
				"account_name": (
					f"{_(d.account_number)} - {_(d.account_name)}" if d.account_number else _(d.account_name)
				),
				"acc_name": d.account_name,
				"acc_number": d.account_number,
			}
		)
		for period in period_list:
			if d.get(period.key) and balance_must_be == "Credit":
				# change sign based on Debit or Credit, since calculation is done using (debit - credit)
				d[period.key] *= -1

			row[period.key] = flt(d.get(period.key, 0.0), 3)

			if abs(row[period.key]) >= get_zero_cutoff(company_currency):
				# ignore zero values
				has_value = True
				total += flt(row[period.key])

		if accumulated_values:
			# when 'accumulated_values' is enabled, periods have running balance.
			# so, last period will have the net amount.
			row["has_value"] = has_value
			row["total"] = flt(d.get(period_list[-1].key, 0.0), 3)
		else:
			row["has_value"] = has_value
			row["total"] = total
		data.append(row)

	return data


def filter_out_zero_value_rows(data, parent_children_map, show_zero_values=False):
	def get_all_parents(account, parent_children_map):
		for parent, children in parent_children_map.items():
			for child in children:
				if child["name"] == account and parent:
					accounts_to_show.add(parent)
					get_all_parents(parent, parent_children_map)

	data_with_value = []
	accounts_to_show = set()

	for d in data:
		if show_zero_values or d.get("has_value"):
			accounts_to_show.add(d.get("account"))
			get_all_parents(d.get("account"), parent_children_map)

	for d in data:
		if d.get("account") in accounts_to_show:
			data_with_value.append(d)

	return data_with_value


def add_total_row(out, root_type, balance_must_be, period_list, company_currency):
	total_row = {
		"account_name": "'" + _("Total {0} ({1})").format(_(root_type), _(balance_must_be)) + "'",
		"account": "'" + _("Total {0} ({1})").format(_(root_type), _(balance_must_be)) + "'",
		"currency": company_currency,
		"opening_balance": 0.0,
	}

	for row in out:
		if not row.get("parent_account"):
			for period in period_list:
				total_row.setdefault(period.key, 0.0)
				total_row[period.key] += row.get(period.key, 0.0)

			total_row.setdefault("total", 0.0)
			total_row["total"] += flt(row["total"])
			total_row["opening_balance"] += row["opening_balance"]

	if "total" in total_row:
		out.append(total_row)

		# blank row after Total
		out.append({})


def get_accounts(company, root_type):
	return frappe.db.sql(
		"""
		select name, account_number, parent_account, lft, rgt, root_type, report_type, account_name, include_in_gross, account_type, is_group, lft, rgt
		from `tabAccount`
		where company=%s and root_type=%s order by lft""",
		(company, root_type),
		as_dict=True,
	)


def filter_accounts(accounts, depth=20):
	parent_children_map = {}
	accounts_by_name = {}
	for d in accounts:
		accounts_by_name[d.name] = d
		parent_children_map.setdefault(d.parent_account or None, []).append(d)

	filtered_accounts = []

	def add_to_list(parent, level):
		if level < depth:
			children = parent_children_map.get(parent) or []
			sort_accounts(children, is_root=True if parent is None else False)

			for child in children:
				child.indent = level
				filtered_accounts.append(child)
				add_to_list(child.name, level + 1)

	add_to_list(None, 0)

	return filtered_accounts, accounts_by_name, parent_children_map


def sort_accounts(accounts, is_root=False, key="name"):
	"""Sort root types as Asset, Liability, Equity, Income, Expense"""

	def compare_accounts(a, b):
		if re.split(r"\W+", a[key])[0].isdigit():
			# if chart of accounts is numbered, then sort by number
			return int(a[key] > b[key]) - int(a[key] < b[key])
		elif is_root:
			if a.report_type != b.report_type and a.report_type == "Balance Sheet":
				return -1
			if a.root_type != b.root_type and a.root_type == "Asset":
				return -1
			if a.root_type == "Liability" and b.root_type == "Equity":
				return -1
			if a.root_type == "Income" and b.root_type == "Expense":
				return -1
		else:
			# sort by key (number) or name
			return int(a[key] > b[key]) - int(a[key] < b[key])
		return 1

	accounts.sort(key=functools.cmp_to_key(compare_accounts))


def set_gl_entries_by_account(
	company,
	from_date,
	to_date,
	filters,
	gl_entries_by_account,
	root_lft=None,
	root_rgt=None,
	root_type=None,
	ignore_closing_entries=False,
	ignore_opening_entries=False,
	group_by_account=False,
	ignore_reporting_currency=True,
):
	"""Returns a dict like { "account": [gl entries], ... }"""
	gl_entries = []

	# For balance sheet
	ignore_closing_balances = frappe.get_single_value("Accounts Settings", "ignore_account_closing_balance")
	if not from_date and not ignore_closing_balances:
		last_period_closing_voucher = frappe.db.get_all(
			"Period Closing Voucher",
			filters={
				"docstatus": 1,
				"company": filters.company,
				"period_end_date": ("<", filters["period_start_date"]),
			},
			fields=["period_end_date", "name"],
			order_by="period_end_date desc",
			limit=1,
		)
		if last_period_closing_voucher:
			gl_entries += get_accounting_entries(
				"Account Closing Balance",
				from_date,
				to_date,
				filters,
				root_lft,
				root_rgt,
				root_type,
				ignore_closing_entries,
				last_period_closing_voucher[0].name,
				group_by_account=group_by_account,
				ignore_reporting_currency=ignore_reporting_currency,
			)
			from_date = add_days(last_period_closing_voucher[0].period_end_date, 1)
			ignore_opening_entries = True

	gl_entries += get_accounting_entries(
		"GL Entry",
		from_date,
		to_date,
		filters,
		root_lft,
		root_rgt,
		root_type,
		ignore_closing_entries,
		ignore_opening_entries=ignore_opening_entries,
		group_by_account=group_by_account,
		ignore_reporting_currency=ignore_reporting_currency,
	)

	if filters and filters.get("presentation_currency") and ignore_reporting_currency:
		convert_to_presentation_currency(gl_entries, get_currency(filters))

	for entry in gl_entries:
		gl_entries_by_account.setdefault(entry.account, []).append(entry)

	return gl_entries_by_account


def get_accounting_entries(
	doctype,
	from_date,
	to_date,
	filters,
	root_lft=None,
	root_rgt=None,
	root_type=None,
	ignore_closing_entries=None,
	period_closing_voucher=None,
	ignore_opening_entries=False,
	group_by_account=False,
	ignore_reporting_currency=True,
):
	gl_entry = frappe.qb.DocType(doctype)
	query = (
		frappe.qb.from_(gl_entry)
		.select(
			gl_entry.account,
			gl_entry.debit if not group_by_account else Sum(gl_entry.debit).as_("debit"),
			gl_entry.credit if not group_by_account else Sum(gl_entry.credit).as_("credit"),
			gl_entry.debit_in_account_currency
			if not group_by_account
			else Sum(gl_entry.debit_in_account_currency).as_("debit_in_account_currency"),
			gl_entry.credit_in_account_currency
			if not group_by_account
			else Sum(gl_entry.credit_in_account_currency).as_("credit_in_account_currency"),
			gl_entry.account_currency,
		)
		.where(gl_entry.company == filters.company)
	)

	if not ignore_reporting_currency:
		query = query.select(
			gl_entry.debit_in_reporting_currency
			if not group_by_account
			else Sum(gl_entry.debit_in_reporting_currency).as_("debit_in_reporting_currency"),
			gl_entry.credit_in_reporting_currency
			if not group_by_account
			else Sum(gl_entry.credit_in_reporting_currency).as_("credit_in_reporting_currency"),
		)

	ignore_is_opening = frappe.get_single_value("Accounts Settings", "ignore_is_opening_check_for_reporting")

	if doctype == "GL Entry":
		query = query.select(gl_entry.posting_date, gl_entry.is_opening, gl_entry.fiscal_year)
		query = query.where(gl_entry.is_cancelled == 0)
		query = query.where(gl_entry.posting_date <= to_date)
		query = query.force_index("posting_date_company_index")

		if ignore_opening_entries and not ignore_is_opening:
			query = query.where(gl_entry.is_opening == "No")
	else:
		query = query.select(gl_entry.closing_date.as_("posting_date"))
		query = query.where(gl_entry.period_closing_voucher == period_closing_voucher)

	query = apply_additional_conditions(doctype, query, from_date, ignore_closing_entries, filters)

	if (root_lft and root_rgt) or root_type:
		account_filter_query = get_account_filter_query(root_lft, root_rgt, root_type, gl_entry)
		query = query.where(ExistsCriterion(account_filter_query))

	from frappe.desk.reportview import build_match_conditions

	query, params = query.walk()
	match_conditions = build_match_conditions(doctype)

	if match_conditions:
		query += "and" + match_conditions

	if group_by_account:
		query += " GROUP BY `account`"

	return frappe.db.sql(query, params, as_dict=True)


def get_account_filter_query(root_lft, root_rgt, root_type, gl_entry):
	acc = frappe.qb.DocType("Account")
	exists_query = (
		frappe.qb.from_(acc).select(acc.name).where(acc.name == gl_entry.account).where(acc.is_group == 0)
	)
	if root_lft and root_rgt:
		exists_query = exists_query.where(acc.lft >= root_lft).where(acc.rgt <= root_rgt)

	if root_type:
		exists_query = exists_query.where(acc.root_type == root_type)

	return exists_query


def apply_additional_conditions(doctype, query, from_date, ignore_closing_entries, filters):
	gl_entry = frappe.qb.DocType(doctype)
	accounting_dimensions = get_accounting_dimensions(as_list=False)

	if ignore_closing_entries:
		if doctype == "GL Entry":
			query = query.where(gl_entry.voucher_type != "Period Closing Voucher")
		else:
			query = query.where(gl_entry.is_period_closing_voucher_entry == 0)

	if from_date and doctype == "GL Entry":
		query = query.where(gl_entry.posting_date >= from_date)

	if filters:
		if filters.get("project"):
			if not isinstance(filters.get("project"), list):
				filters.project = frappe.parse_json(filters.get("project"))

			query = query.where(gl_entry.project.isin(filters.project))

		if filters.get("cost_center"):
			filters.cost_center = get_cost_centers_with_children(filters.cost_center)
			query = query.where(gl_entry.cost_center.isin(filters.cost_center))

		if filters.get("include_default_book_entries"):
			company_fb = frappe.get_cached_value("Company", filters.company, "default_finance_book")

			if filters.finance_book and company_fb and cstr(filters.finance_book) != cstr(company_fb):
				frappe.throw(
					_("To use a different finance book, please uncheck 'Include Default FB Entries'")
				)

			query = query.where(
				(gl_entry.finance_book.isin([cstr(filters.finance_book), cstr(company_fb), ""]))
				| (gl_entry.finance_book.isnull())
			)
		else:
			query = query.where(
				(gl_entry.finance_book.isin([cstr(filters.finance_book), ""]))
				| (gl_entry.finance_book.isnull())
			)

	if accounting_dimensions:
		for dimension in accounting_dimensions:
			if filters.get(dimension.fieldname):
				if frappe.get_cached_value("DocType", dimension.document_type, "is_tree"):
					filters[dimension.fieldname] = get_dimension_with_children(
						dimension.document_type, filters.get(dimension.fieldname)
					)

				query = query.where(gl_entry[dimension.fieldname].isin(filters[dimension.fieldname]))

	return query


def get_cost_centers_with_children(cost_centers):
	if not isinstance(cost_centers, list):
		cost_centers = [d.strip() for d in cost_centers.strip().split(",") if d]

	all_cost_centers = []
	for d in cost_centers:
		if frappe.db.exists("Cost Center", d):
			lft, rgt = frappe.db.get_value("Cost Center", d, ["lft", "rgt"])
			children = frappe.get_all("Cost Center", filters={"lft": [">=", lft], "rgt": ["<=", rgt]})
			all_cost_centers += [c.name for c in children]
		else:
			frappe.throw(_("Cost Center: {0} does not exist").format(d))

	return list(set(all_cost_centers))


def get_columns(periodicity, period_list, accumulated_values=1, company=None, cash_flow=False):
	columns = [
		{
			"fieldname": "account" if not cash_flow else "section",
			"label": _("Account") if not cash_flow else _("Section"),
			"fieldtype": "Link",
			"options": "Account",
			"width": 300,
		}
	]
	if not cash_flow:
		columns.extend(
			[
				{
					"fieldname": "acc_name",
					"label": _("Account Name"),
					"fieldtype": "Data",
					"width": 250,
					"hidden": 1,
				},
				{
					"fieldname": "acc_number",
					"label": _("Account Number"),
					"fieldtype": "Data",
					"width": 120,
					"hidden": 1,
				},
			]
		)
	if company:
		columns.append(
			{
				"fieldname": "currency",
				"label": _("Currency"),
				"fieldtype": "Link",
				"options": "Currency",
				"hidden": 1,
			}
		)
	for period in period_list:
		columns.append(
			{
				"fieldname": period.key,
				"label": period.label,
				"fieldtype": "Currency",
				"options": "currency",
				"width": 150,
			}
		)
	if periodicity != "Yearly":
		if not accumulated_values:
			columns.append(
				{
					"fieldname": "total",
					"label": _("Total"),
					"fieldtype": "Currency",
					"width": 150,
					"options": "currency",
				}
			)

	return columns


def get_filtered_list_for_consolidated_report(filters, period_list):
	filtered_summary_list = []
	for period in period_list:
		if period == filters.get("company"):
			filtered_summary_list.append(period)

	return filtered_summary_list


def compute_growth_view_data(data, columns):
	data_copy = copy.deepcopy(data)

	for row_idx in range(len(data_copy)):
		for column_idx in range(1, len(columns)):
			previous_period_key = columns[column_idx - 1].get("key")
			current_period_key = columns[column_idx].get("key")
			current_period_value = data_copy[row_idx].get(current_period_key)
			previous_period_value = data_copy[row_idx].get(previous_period_key)
			annual_growth = 0

			if current_period_value is None:
				data[row_idx][current_period_key] = None
				continue

			if previous_period_value == 0 and current_period_value > 0:
				annual_growth = 1

			elif previous_period_value > 0:
				annual_growth = (current_period_value - previous_period_value) / previous_period_value

			growth_percent = round(annual_growth * 100, 2)

			data[row_idx][current_period_key] = growth_percent


def compute_margin_view_data(data, columns, accumulated_values):
	if not columns:
		return

	if not accumulated_values:
		columns.append({"key": "total"})

	data_copy = copy.deepcopy(data)

	base_row = None
	for row in data_copy:
		if row.get("account_name") == _("Income"):
			base_row = row
			break

	if not base_row:
		return

	for row_idx in range(len(data_copy)):
		# Taking the total income from each column (for all the financial years) as the base (100%)
		row = data_copy[row_idx]
		if not row:
			continue

		for column in columns:
			curr_period = column.get("key")
			base_value = base_row[curr_period]
			curr_value = row[curr_period]

			if curr_value is None or base_value <= 0:
				data[row_idx][curr_period] = None
				continue

			margin_percent = round((curr_value / base_value) * 100, 2)

			data[row_idx][curr_period] = margin_percent
