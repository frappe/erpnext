# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, getdate, formatdate, cstr
from erpnext.accounts.report.financial_statements import filter_accounts
from erpnext.accounts.report.trial_balance.trial_balance import validate_filters

value_fields = ("income", "expense", "total")

def execute(filters=None):
	validate_filters(filters)
	data = get_data(filters)
	columns = get_columns()
	return columns, data

def get_data(filters):
	accounts = frappe.db.sql("""select name, parent_cost_center as parent_account, cost_center_name as account_name, lft, rgt
		from `tabCost Center` where company=%s order by lft""", filters.company, as_dict=True)

	if not accounts:
		return None

	accounts, accounts_by_name, parent_children_map = filter_accounts(accounts)

	min_lft, max_rgt = frappe.db.sql("""select min(lft), max(rgt) from `tabCost Center`
		where company=%s""", (filters.company,))[0]

	gl_entries_by_account = {}

	set_gl_entries_by_account(filters.company, filters.from_date,
		filters.to_date, min_lft, max_rgt, gl_entries_by_account, ignore_closing_entries=not flt(filters.with_period_closing_entry))

	total_row = calculate_values(accounts, gl_entries_by_account, filters)
	accumulate_values_into_parents(accounts, accounts_by_name)

	data = prepare_data(accounts, filters, total_row, parent_children_map)

	return data

def calculate_values(accounts, gl_entries_by_account, filters):
	init = {
		"income": 0.0,
		"expense": 0.0,
		"total": 0.0
	}

	total_row = {
		"cost_center": None,
		"account_name": "'" + _("Total") + "'",
		"warn_if_negative": True,
		"income": 0.0,
		"expense": 0.0,
		"total": 0.0
	}

	for d in accounts:
		d.update(init.copy())

		# add opening

		for entry in gl_entries_by_account.get(d.name, []):
			if cstr(entry.is_opening) != "Yes":
				if entry.type == 'Income':
					d["income"] += flt(entry.credit) - flt(entry.debit)
				if entry.type == 'Expense':
					d["expense"] += flt(entry.debit) - flt(entry.credit)

				d["total"] = d.get("income") - d.get("expense")

		total_row["income"] += d["income"]
		total_row["expense"] += d["expense"]

	total_row["total"] = total_row.get("income") - total_row.get("expense")

	return total_row

def accumulate_values_into_parents(accounts, accounts_by_name):
	for d in reversed(accounts):
		if d.parent_account:
			for key in value_fields:
				accounts_by_name[d.parent_account][key] += d[key]

def prepare_data(accounts, filters, total_row, parent_children_map):
	data = []
	company_currency = frappe.db.get_value("Company", filters.company, "default_currency")

	for d in accounts:
		has_value = False
		row = {
			"account_name": d.account_name,
			"account": d.name,
			"parent_account": d.parent_account,
			"indent": d.indent,
			"from_date": filters.from_date,
			"to_date": filters.to_date,
			"currency": company_currency
		}

		for key in value_fields:
			row[key] = flt(d.get(key, 0.0), 3)
			
			if abs(row[key]) >= 0.005:
				# ignore zero values
				has_value = True

		row["has_value"] = has_value
		data.append(row)
		
	data.extend([{},total_row])

	return data

def get_columns():
	return [
		{
			"fieldname": "account",
			"label": _("Cost Center"),
			"fieldtype": "Link",
			"options": "Cost Center",
			"width": 300
		},
		{
			"fieldname": "income",
			"label": _("Income"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120
		},
		{
			"fieldname": "expense",
			"label": _("Expense"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120
		},
		{
			"fieldname": "total",
			"label": _("Gross Profit / Loss"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120
		},
		{
			"fieldname": "currency",
			"label": _("Currency"),
			"fieldtype": "Link",
			"options": "Currency",
			"hidden": 1
		}
	]

def set_gl_entries_by_account(company, from_date, to_date, root_lft, root_rgt, gl_entries_by_account,
		ignore_closing_entries=False):
	"""Returns a dict like { "account": [gl entries], ... }"""
	additional_conditions = []

	if ignore_closing_entries:
		additional_conditions.append("and ifnull(voucher_type, '')!='Period Closing Voucher'")

	if from_date:
		additional_conditions.append("and posting_date >= %(from_date)s")

	gl_entries = frappe.db.sql("""select posting_date, cost_center, debit, credit, 
		is_opening, (select root_type from `tabAccount` where name = account) as type
		from `tabGL Entry` where company=%(company)s
		{additional_conditions}
		and posting_date <= %(to_date)s
		and cost_center in (select name from `tabCost Center`
			where lft >= %(lft)s and rgt <= %(rgt)s)
		order by cost_center, posting_date""".format(additional_conditions="\n".join(additional_conditions)),
		{
			"company": company,
			"from_date": from_date,
			"to_date": to_date,
			"lft": root_lft,
			"rgt": root_rgt
		},
		as_dict=True)

	for entry in gl_entries:
		gl_entries_by_account.setdefault(entry.cost_center, []).append(entry)

	return gl_entries_by_account