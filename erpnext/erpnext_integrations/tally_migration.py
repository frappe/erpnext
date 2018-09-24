# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
import traceback
from erpnext import encode_company_abbr
from frappe.utils.nestedset import rebuild_tree


@frappe.whitelist()
def create_chart_of_accounts(company, accounts):
	accounts = json.loads(accounts)

	frappe.local.flags.ignore_on_update = True
	create_root_accounts(company)
	create_accounts(company, accounts)
	rebuild_tree("Account", "parent_account")
	frappe.db.commit()

	frappe.clear_messages()


def create_root_accounts(company):
	root_accounts = [
		("Assets", "Asset"),
		("Expenses", "Expense"),
		("Incomes", "Income"),
		("Liabilities", "Liability")
	]
	for account, root_type in root_accounts:
		try:
			account_name = encode_company_abbr(account, company)
			if not frappe.db.exists({"doctype": "Account", "name": account_name, "company": company}):
				frappe.get_doc({
					"doctype": "Account",
					"account_name": account,
					"root_type": root_type,
					"is_group": 1,
					"company": company,
				}).insert(ignore_mandatory=True)
		except:
			traceback.print_exc()
			print(account)


def create_accounts(company, accounts):
	accounts = resolve_name_conflicts(accounts)
	for account in accounts:
		try:
			account_name = encode_company_abbr(account["account_name"], company)
			if not frappe.db.exists({"doctype": "Account", "name": account_name, "company": company}):
				frappe.get_doc({
					"doctype": "Account",
					"account_name": account["account_name"],
					"parent_account": encode_company_abbr(account["parent_account"], company),
					"is_group": account["is_group"],
					"company": company,
				}).insert()
		except:
			traceback.print_exc()
			print(account)


def resolve_name_conflicts(accounts):
	group_accounts = [a["account_name"] for a in accounts if a["is_group"]]
	non_group_accounts = [a["account_name"] for a in accounts if not a["is_group"]]
	common = set(group_accounts).intersection(non_group_accounts)
	for account in accounts:
		if any(account[field] in common for field in ("account_name", "parent_account")):
			if account["is_group"]:
				account["account_name"] = "{} - Group".format(account["account_name"])
			else:
				account["parent_account"] = "{} - Group".format(account["parent_account"])
	return accounts
