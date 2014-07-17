# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import babel.dates
import frappe
from frappe.utils import (cstr, flt, cint,
	getdate, get_first_day, get_last_day, add_months, add_days, now_datetime)
from frappe import _

def execute(filters=None):
	company = filters.company
	fiscal_year = filters.fiscal_year
	depth = cint(filters.depth) or 3
	start_date, end_date = frappe.db.get_value("Fiscal Year", fiscal_year, ["year_start_date", "year_end_date"])
	period_list = get_period_list(start_date, end_date, filters.get("periodicity") or "Yearly", fiscal_year)

	out = []
	for (root_type, balance_must_be) in (("Asset", "Debit"), ("Liability", "Credit"), ("Equity", "Credit")):
		data = []
		accounts, account_gl_entries = get_accounts_and_gl_entries(root_type, company, end_date)
		if accounts:
			accounts, accounts_map = filter_accounts(accounts, depth=depth)

			for d in accounts:
				for account_name in ([d.name] + (d.invisible_children or [])):
					for each in account_gl_entries.get(account_name, []):
						for period_start_date, period_end_date, period_key, period_label in period_list:
							each.posting_date = getdate(each.posting_date)

							# check if posting date is within the period
							if ((not period_start_date or (each.posting_date >= period_start_date))
								and (each.posting_date <= period_end_date)):

								d[period_key] = d.get(period_key, 0.0) + flt(each.debit) - flt(each.credit)

			for d in reversed(accounts):
				if d.parent_account:
					for period_start_date, period_end_date, period_key, period_label in period_list:
						accounts_map[d.parent_account][period_key] = accounts_map[d.parent_account].get(period_key, 0.0) + d.get(period_key, 0.0)

			for i, d in enumerate(accounts):
				has_value = False
				row = {"account_name": d["account_name"], "account": d["name"], "indent": d["indent"], "parent_account": d["parent_account"]}
				for period_start_date, period_end_date, period_key, period_label in period_list:
					if d.get(period_key):
						d[period_key] *= (1 if balance_must_be=="Debit" else -1)

					row[period_key] = d.get(period_key, 0.0)
					if row[period_key]:
						has_value = True

				if has_value:
					data.append(row)

		if data:
			row = {"account_name": _("Total ({0})").format(balance_must_be), "account": None}
			for period_start_date, period_end_date, period_key, period_label in period_list:
				if period_key in data[0]:
					row[period_key] = data[0].get(period_key, 0.0)
					data[0][period_key] = ""

			data.append(row)

			# blank row after Total
			data.append({})

		out.extend(data)

	columns = [{"fieldname": "account", "label": _("Account"), "fieldtype": "Link", "options": "Account", "width": 300}]
	for period_start_date, period_end_date, period_key, period_label in period_list:
		columns.append({"fieldname": period_key, "label": period_label, "fieldtype": "Currency", "width": 150})

	return columns, out

def get_accounts_and_gl_entries(root_type, company, end_date):
	# root lft, rgt
	root_account = frappe.db.sql("""select lft, rgt from `tabAccount`
		where company=%s and root_type=%s order by lft limit 1""",
		(company, root_type), as_dict=True)

	if not root_account:
		return None, None

	lft, rgt = root_account[0].lft, root_account[0].rgt

	accounts = frappe.db.sql("""select * from `tabAccount`
		where company=%(company)s and lft >= %(lft)s and rgt <= %(rgt)s order by lft""",
		{ "company": company, "lft": lft, "rgt": rgt }, as_dict=True)

	gl_entries = frappe.db.sql("""select * from `tabGL Entry`
		where company=%(company)s
		and posting_date <= %(end_date)s
		and account in (select name from `tabAccount`
			where lft >= %(lft)s and rgt <= %(rgt)s)""",
		{
			"company": company,
			"end_date": end_date,
			"lft": lft,
			"rgt": rgt
		},
		as_dict=True)

	account_gl_entries = {}
	for entry in gl_entries:
		account_gl_entries.setdefault(entry.account, []).append(entry)

	return accounts, account_gl_entries

def filter_accounts(accounts, depth):
	parent_children_map = {}
	accounts_map = {}
	for d in accounts:
		accounts_map[d.name] = d
		parent_children_map.setdefault(d.parent_account or None, []).append(d)

	data = []
	def add_to_data(parent, level):
		if level < depth:
			for child in (parent_children_map.get(parent) or []):
				child.indent = level
				data.append(child)
				add_to_data(child.name, level + 1)

		else:
			# include all children at level lower than the depth
			parent_account = accounts_map[parent]
			parent_account["invisible_children"] = []
			for d in accounts:
				if d.lft > parent_account.lft and d.rgt < parent_account.rgt:
					parent_account["invisible_children"].append(d.name)

	add_to_data(None, 0)

	return data, accounts_map

def get_period_list(start_date, end_date, periodicity, fiscal_year):
	"""Get a list of tuples that represents (period_start_date, period_end_date, period_key)
		Periodicity can be (Yearly, Quarterly, Monthly)"""

	start_date = getdate(start_date)
	end_date = getdate(end_date)
	today = now_datetime().date()

	if periodicity == "Yearly":
		period_list = [(None, end_date, fiscal_year, fiscal_year)]
	else:
		months_to_add = {
			"Half-yearly": 6,
			"Quarterly": 3,
			"Monthly": 1
		}[periodicity]

		period_list = []

		# start with first day, so as to avoid year start dates like 2-April if every they occur
		next_date = get_first_day(start_date)

		for i in xrange(12 / months_to_add):
			next_date = add_months(next_date, months_to_add)

			if next_date == get_first_day(next_date):
				# if first day, get the last day of previous month
				next_date = add_days(next_date, -1)
			else:
				# get the last day of the month
				next_date = get_last_day(next_date)

			# checking in the middle of the fiscal year? don't show future periods
			if next_date > today:
				break

			elif next_date <= end_date:
				key = next_date.strftime("%b_%Y").lower()
				label = babel.dates.format_date(next_date, "MMM YYYY", locale=(frappe.local.lang or "").replace("-", "_"))
				period_list.append((None, next_date, key, label))

				# if it ends before a full year
				if next_date == end_date:
					break

			else:
				# if it ends before a full year
				key = end_date.strftime("%b_%Y").lower()
				label = babel.dates.format_date(end_date, "MMM YYYY", locale=(frappe.local.lang or "").replace("-", "_"))
				period_list.append((None, end_date, key, label))
				break

	return period_list
