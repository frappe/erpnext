# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, formatdate
from erpnext.accounts.report.financial_statements import filter_accounts, get_gl_entries

value_fields = ("opening_debit", "opening_credit", "debit", "credit", "closing_debit", "closing_credit")

def execute(filters):
	validate_filters(filters)
	data = get_data(filters)
	columns = get_columns()
	return columns, data

def validate_filters(filters):
	filters.year_start_date, filters.year_end_date = frappe.db.get_value("Fiscal Year", filters.fiscal_year,
		["year_start_date", "year_end_date"])
	filters.year_start_date = getdate(filters.year_start_date)
	filters.year_end_date = getdate(filters.year_end_date)

	if not filters.from_date:
		filters.from_date = filters.year_start_date

	if not filters.to_date:
		filters.to_date = filters.year_end_date

	filters.from_date = getdate(filters.from_date)
	filters.to_date = getdate(filters.to_date)

	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date cannot be greater than To Date"))

	if (filters.from_date < filters.year_start_date) or (filters.from_date > filters.year_end_date):
		frappe.msgprint(_("From Date should be within the Fiscal Year. Assuming From Date = {0}")\
			.format(formatdate(filters.year_start_date)))

		filters.from_date = filters.year_start_date

	if (filters.to_date < filters.year_start_date) or (filters.to_date > filters.year_end_date):
		frappe.msgprint(_("To Date should be within the Fiscal Year. Assuming To Date = {0}")\
			.format(formatdate(filters.year_end_date)))
		filters.to_date = filters.year_end_date

def get_data(filters):
	accounts = frappe.db.sql("""select * from `tabAccount` where company=%s order by lft""",
		filters.company, as_dict=True)

	if not accounts:
		return None

	accounts, accounts_by_name = filter_accounts(accounts)

	min_lft, max_rgt = frappe.db.sql("""select min(lft), max(rgt) from `tabAccount`
		where company=%s""", (filters.company,))[0]

	gl_entries_by_account = get_gl_entries(filters.company, None, filters.to_date, min_lft, max_rgt,
		ignore_closing_entries=not flt(filters.with_period_closing_entry))

	total_row = calculate_values(accounts, gl_entries_by_account, filters)
	accumulate_values_into_parents(accounts, accounts_by_name)

	data = prepare_data(accounts, filters, total_row)

	return data

def calculate_values(accounts, gl_entries_by_account, filters):
	init = {
		"opening_debit": 0.0,
		"opening_credit": 0.0,
		"debit": 0.0,
		"credit": 0.0,
		"closing_debit": 0.0,
		"closing_credit": 0.0
	}

	total_row = {
		"account": None,
		"account_name": _("Total"),
		"warn_if_negative": True,
		"debit": 0.0,
		"credit": 0.0
	}

	for d in accounts:
		d.update(init.copy())

		for entry in gl_entries_by_account.get(d.name, []):
			posting_date = getdate(entry.posting_date)

			# opening
			if posting_date < filters.from_date:
				is_valid_opening = (d.root_type in ("Asset", "Liability", "Equity") or
					(filters.year_start_date <= posting_date < filters.from_date))

				if is_valid_opening:
					d["opening_debit"] += flt(entry.debit)
					d["opening_credit"] += flt(entry.credit)

			elif posting_date <= filters.to_date:

				if entry.is_opening == "Yes" and d.root_type in ("Asset", "Liability", "Equity"):
					d["opening_debit"] += flt(entry.debit)
					d["opening_credit"] += flt(entry.credit)

				else:
					d["debit"] += flt(entry.debit)
					d["credit"] += flt(entry.credit)

		total_row["debit"] += d["debit"]
		total_row["credit"] += d["credit"]

	return total_row

def accumulate_values_into_parents(accounts, accounts_by_name):
	for d in reversed(accounts):
		if d.parent_account:
			for key in value_fields:
				accounts_by_name[d.parent_account][key] += d[key]

def prepare_data(accounts, filters, total_row):
	show_zero_values = cint(filters.show_zero_values)
	data = []
	for i, d in enumerate(accounts):
		has_value = False
		row = {
			"account_name": d.account_name,
			"account": d.name,
			"parent_account": d.parent_account,
			"indent": d.indent,
			"from_date": filters.from_date,
			"to_date": filters.to_date
		}

		prepare_opening_and_closing(d)

		for key in value_fields:
			row[key] = d.get(key, 0.0)
			if row[key]:
				has_value = True

		if has_value or show_zero_values:
			data.append(row)

	data.extend([{},total_row])

	return data

def get_columns():
	return [
		{
			"fieldname": "account",
			"label": _("Account"),
			"fieldtype": "Link",
			"options": "Account",
			"width": 300
		},
		{
			"fieldname": "opening_debit",
			"label": _("Opening (Dr)"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "opening_credit",
			"label": _("Opening (Cr)"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "debit",
			"label": _("Debit"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "credit",
			"label": _("Credit"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "closing_debit",
			"label": _("Closing (Dr)"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "closing_credit",
			"label": _("Closing (Cr)"),
			"fieldtype": "Currency",
			"width": 120
		}
	]

def prepare_opening_and_closing(d):
	d["closing_debit"] = d["opening_debit"] + d["debit"]
	d["closing_credit"] = d["opening_credit"] + d["credit"]

	if d["closing_debit"] > d["closing_credit"]:
		d["closing_debit"] -= d["closing_credit"]
		d["closing_credit"] = 0.0

	else:
		d["closing_credit"] -= d["closing_debit"]
		d["closing_debit"] = 0.0

	if d["opening_debit"] > d["opening_credit"]:
		d["opening_debit"] -= d["opening_credit"]
		d["opening_credit"] = 0.0

	else:
		d["opening_credit"] -= d["opening_debit"]
		d["opening_debit"] = 0.0
