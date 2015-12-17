# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, _dict
from frappe.utils import (flt, getdate, get_first_day, get_last_day,
	add_months, add_days, formatdate)

def get_period_list(fiscal_year, periodicity, from_beginning=False):
	"""Get a list of dict {"to_date": to_date, "key": key, "label": label}
		Periodicity can be (Yearly, Quarterly, Monthly)"""

	fy_start_end_date = frappe.db.get_value("Fiscal Year", fiscal_year, ["year_start_date", "year_end_date"])
	if not fy_start_end_date:
		frappe.throw(_("Fiscal Year {0} not found.").format(fiscal_year))

	start_date = getdate(fy_start_end_date[0])
	end_date = getdate(fy_start_end_date[1])

	if periodicity == "Yearly":
		period_list = [_dict({"to_date": end_date, "key": fiscal_year, "label": fiscal_year})]
	else:
		months_to_add = {
			"Half-yearly": 6,
			"Quarterly": 3,
			"Monthly": 1
		}[periodicity]

		period_list = []

		# start with first day, so as to avoid year to_dates like 2-April if ever they occur
		to_date = get_first_day(start_date)

		for i in xrange(12 / months_to_add):
			to_date = add_months(to_date, months_to_add)

			if to_date == get_first_day(to_date):
				# if to_date is the first day, get the last day of previous month
				to_date = add_days(to_date, -1)
			else:
				# to_date should be the last day of the new to_date's month
				to_date = get_last_day(to_date)

			if to_date <= end_date:
				# the normal case
				period_list.append(_dict({ "to_date": to_date }))

				# if it ends before a full year
				if to_date == end_date:
					break

			else:
				# if a fiscal year ends before a 12 month period
				period_list.append(_dict({ "to_date": end_date }))
				break

	# common processing
	for opts in period_list:
		key = opts["to_date"].strftime("%b_%Y").lower()
		label = formatdate(opts["to_date"], "MMM YYYY")
		opts.update({
			"key": key.replace(" ", "_").replace("-", "_"),
			"label": label,
			"year_start_date": start_date,
			"year_end_date": end_date
		})

		if from_beginning:
			# set start date as None for all fiscal periods, used in case of Balance Sheet
			opts["from_date"] = None
		else:
			opts["from_date"] = start_date

	return period_list

def get_data(company, root_type, balance_must_be, period_list, ignore_closing_entries=False):
	accounts = get_accounts(company, root_type)
	if not accounts:
		return None

	accounts, accounts_by_name = filter_accounts(accounts)

	gl_entries_by_account = {}
	for root in frappe.db.sql("""select lft, rgt from tabAccount
			where root_type=%s and ifnull(parent_account, '') = ''""", root_type, as_dict=1):
		set_gl_entries_by_account(company, period_list[0]["from_date"],
			period_list[-1]["to_date"],root.lft, root.rgt, gl_entries_by_account,
			ignore_closing_entries=ignore_closing_entries)

	calculate_values(accounts_by_name, gl_entries_by_account, period_list)
	accumulate_values_into_parents(accounts, accounts_by_name, period_list)
	out = prepare_data(accounts, balance_must_be, period_list)

	if out:
		add_total_row(out, balance_must_be, period_list)

	return out

def calculate_values(accounts_by_name, gl_entries_by_account, period_list):
	for entries in gl_entries_by_account.values():
		for entry in entries:
			d = accounts_by_name.get(entry.account)
			for period in period_list:
				# check if posting date is within the period
				if entry.posting_date <= period.to_date:
					d[period.key] = d.get(period.key, 0.0) + flt(entry.debit) - flt(entry.credit)

def accumulate_values_into_parents(accounts, accounts_by_name, period_list):
	"""accumulate children's values in parent accounts"""
	for d in reversed(accounts):
		if d.parent_account:
			for period in period_list:
				accounts_by_name[d.parent_account][period.key] = accounts_by_name[d.parent_account].get(period.key, 0.0) + \
					d.get(period.key, 0.0)

def prepare_data(accounts, balance_must_be, period_list):
	out = []
	year_start_date = period_list[0]["year_start_date"].strftime("%Y-%m-%d")
	year_end_date = period_list[-1]["year_end_date"].strftime("%Y-%m-%d")

	for d in accounts:
		# add to output
		has_value = False
		row = {
			"account_name": d.account_name,
			"account": d.name,
			"parent_account": d.parent_account,
			"indent": flt(d.indent),
			"from_date": year_start_date,
			"to_date": year_end_date
		}
		for period in period_list:
			if d.get(period.key):
				# change sign based on Debit or Credit, since calculation is done using (debit - credit)
				d[period.key] *= (1 if balance_must_be=="Debit" else -1)

			row[period.key] = flt(d.get(period.key, 0.0), 3)

			if abs(row[period.key]) >= 0.005:
				# ignore zero values
				has_value = True

		if has_value:
			out.append(row)

	return out

def add_total_row(out, balance_must_be, period_list):
	total_row = {
		"account_name": "'" + _("Total ({0})").format(balance_must_be) + "'",
		"account": None
	}

	for row in out:
		if not row.get("parent_account"):
			for period in period_list:
				total_row.setdefault(period.key, 0.0)
				total_row[period.key] += row.get(period.key, 0.0)

			row[period.key] = ""

	out.append(total_row)

	# blank row after Total
	out.append({})

def get_accounts(company, root_type):
	return frappe.db.sql("""select name, parent_account, lft, rgt, root_type, report_type, account_name from `tabAccount`
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
			if parent == None:
				sort_root_accounts(children)

			for child in children:
				child.indent = level
				filtered_accounts.append(child)
				add_to_list(child.name, level + 1)

	add_to_list(None, 0)

	return filtered_accounts, accounts_by_name

def sort_root_accounts(roots):
	"""Sort root types as Asset, Liability, Equity, Income, Expense"""

	def compare_roots(a, b):
		if a.report_type != b.report_type and a.report_type == "Balance Sheet":
			return -1
		if a.root_type != b.root_type and a.root_type == "Asset":
			return -1
		if a.root_type == "Liability" and b.root_type == "Equity":
			return -1
		if a.root_type == "Income" and b.root_type == "Expense":
			return -1
		return 1

	roots.sort(compare_roots)

def set_gl_entries_by_account(company, from_date, to_date, root_lft, root_rgt, gl_entries_by_account,
		ignore_closing_entries=False):
	"""Returns a dict like { "account": [gl entries], ... }"""
	additional_conditions = []

	if ignore_closing_entries:
		additional_conditions.append("and ifnull(voucher_type, '')!='Period Closing Voucher'")

	if from_date:
		additional_conditions.append("and posting_date >= %(from_date)s")

	gl_entries = frappe.db.sql("""select posting_date, account, debit, credit, is_opening from `tabGL Entry`
		where company=%(company)s
		{additional_conditions}
		and posting_date <= %(to_date)s
		and account in (select name from `tabAccount`
			where lft >= %(lft)s and rgt <= %(rgt)s)
		order by account, posting_date""".format(additional_conditions="\n".join(additional_conditions)),
		{
			"company": company,
			"from_date": from_date,
			"to_date": to_date,
			"lft": root_lft,
			"rgt": root_rgt
		},
		as_dict=True)

	for entry in gl_entries:
		gl_entries_by_account.setdefault(entry.account, []).append(entry)

	return gl_entries_by_account

def get_columns(period_list):
	columns = [{
		"fieldname": "account",
		"label": _("Account"),
		"fieldtype": "Link",
		"options": "Account",
		"width": 300
	}]
	for period in period_list:
		columns.append({
			"fieldname": period.key,
			"label": period.label,
			"fieldtype": "Currency",
			"width": 150
		})

	return columns