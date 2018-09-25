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


@frappe.whitelist()
def create_parties(company, parties):
	parties = json.loads(parties)
	make_custom_fields(["Customer", "Supplier"], "company")
	_create_parties(company, parties)
	frappe.db.commit()
	frappe.clear_messages()


@frappe.whitelist()
def create_vouchers(company, vouchers):
	vouchers = json.loads(vouchers)
	make_custom_fields(["Journal Entry"], "tally_id")
	_create_vouchers(company, vouchers)
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


def make_custom_fields(doctypes, field_name):
	for doctype in doctypes:
		if not frappe.db.exists({"doctype": "Custom Field", "dt": doctype, "fieldname": field_name}):
			frappe.get_doc({
				"doctype": "Custom Field",
				"label": "Tally ID",
				"dt": doctype,
				"fieldname": field_name,
				"fieldtype": "Data",
			}).insert()


def _create_parties(company, parties):
	for party in parties:
		try:
			if party["party_type"] == "Customer":
				if not frappe.db.exists({"doctype": "Customer", "customer_name": party["party_name"], "company": company}):
					frappe.get_doc({
						"doctype": "Customer",
						"customer_name": party["party_name"],
						"customer_group": "All Customer Groups",
						"customer_territory": "All Territories",
						"customer_type": "Individual",
						"company": company,
					}).insert()
			elif party["party_type"] == "Supplier":
				if not frappe.db.exists({"doctype": "Supplier", "supplier_name": party["party_name"], "company": company}):
					frappe.get_doc({
						"doctype": "Supplier",
						"supplier_name": party["party_name"],
						"supplier_group": "All Supplier Groups",
						"supplier_type": "Individual",
						"company": company,
					}).insert()
		except:
			traceback.print_exc()
			print(party)


def _create_vouchers(company, vouchers):
	for voucher in vouchers:
		try:
			voucher_type_mapping = {
				"Journal": create_journal_voucher,
			}
			function = voucher_type_mapping[voucher["voucher_type"]]
			function(company, voucher)
		except:
			import traceback
			traceback.print_exc()


def create_journal_voucher(company, voucher):
	try:
		if not frappe.db.exists({"doctype": "Journal Entry", "tally_id": voucher["guid"], "company": company}):
			for account in voucher["accounts"]:
				if account["is_party"]:
					if frappe.db.exists({"doctype": "Customer", "customer_name": account["account"], "company": company}):
						account["party_type"] = "Customer"
						account["party"] = account["account"]
						account["account"] = "Sundry Debtors"
					elif frappe.db.exists({"doctype": "Supplier", "supplier_name": account["account"], "company": company}):
						account["party_type"] = "Supplier"
						account["party"] = account["account"]
						account["account"] = "Sundry Creditors"
				account["account"] = encode_company_abbr(account["account"], company)

			frappe.get_doc({
				"doctype": "Journal Entry",
				"naming_series": "JV-",
				"tally_id": voucher["guid"],
				"posting_date": voucher["posting_date"],
				"company": company,
				"accounts": voucher["accounts"],
			}).insert().submit()
	except:
		traceback.print_exc()
		print(voucher)


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


@frappe.whitelist()
def clean_all():
	frappe.db.sql("""DELETE FROM `tabAccount`""")
	frappe.db.sql("""DELETE FROM `tabCustomer`""")
	frappe.db.sql("""DELETE FROM `tabSupplier`""")
	frappe.db.sql("""DELETE FROM `tabJournal Entry`""")
	frappe.db.sql("""DELETE FROM `tabGL Entry`""")
	frappe.db.commit()
