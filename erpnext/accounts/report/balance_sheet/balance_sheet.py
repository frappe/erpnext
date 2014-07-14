# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, flt
from frappe import _

def execute(filters=None):
	company = filters.company
	fiscal_year = filters.fiscal_year
	depth = 3
	end_date = frappe.db.get_value("Fiscal Year", fiscal_year, "year_end_date")

	for root_type, balance_must_be in (("Asset", "Debit"), ("Liability", "Credit"), ("Equity", "Credit")):
		accounts, account_gl_entries = get_accounts_and_gl_entries(root_type, company, end_date)
		if accounts:
			accounts, accounts_map = filter_accounts(accounts, depth=depth)

			for d in accounts:
				d.debit = d.credit = 0
				for account_name in ([d.name] + (d.invisible_children or [])):
					for each in account_gl_entries.get(account_name, []):
						d.debit += flt(each.debit)
						d.credit += flt(each.credit)

			for d in reversed(accounts):
				if d.parent_account:
					accounts_map[d.parent_account]["debit"] += d.debit
					accounts_map[d.parent_account]["credit"] += d.credit

			for d in accounts:
				d.balance = d["debit"] - d["credit"]
				if d.balance:
					d.balance *= (1 if balance_must_be=="Debit" else -1)
				print (" " * d["indent"] * 2) + d["account_name"], d["balance"], balance_must_be

	return [], []

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
