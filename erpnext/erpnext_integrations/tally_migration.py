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
	saved_accounts = list(create_accounts(company, accounts))
	rebuild_tree("Account", "parent_account")
	frappe.db.commit()

	frappe.clear_messages()
	return saved_accounts

@frappe.whitelist()
def create_parties(company, parties):
	parties = json.loads(parties)
	make_custom_fields(["Customer", "Supplier"], "company")
	saved_parties = list(_create_parties(company, parties))
	frappe.db.commit()
	frappe.clear_messages()
	return saved_parties


@frappe.whitelist()
def create_items(company, items):
	items = json.loads(items)
	make_custom_fields(["Item"], "company")
	saved_items = list(_create_items(items))
	frappe.db.commit()
	frappe.clear_messages()
	return saved_items

@frappe.whitelist()
def create_vouchers(company, vouchers):
	vouchers = json.loads(vouchers)
	make_custom_fields(["Journal Entry", "Purchase Invoice", "Sales Invoice"], "tally_id")
	saved_vouchers = list(_create_vouchers(vouchers))
	frappe.db.commit()
	frappe.clear_messages()
	return saved_vouchers

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
			if not frappe.db.exists("Account", account_name):
				account_type = {"Sundry Debtors": "Receivable", "Sundry Creditors": "Payable"}.get(account["account_name"])
				yield frappe.get_doc({
					"doctype": "Account",
					"account_name": account["account_name"],
					"parent_account": encode_company_abbr(account["parent_account"], company),
					"account_type": account_type,
					"is_group": account["is_group"],
					"company": company,
				}).insert().as_dict()
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
					yield frappe.get_doc({
						"doctype": "Customer",
						"customer_name": party["party_name"],
						"customer_group": "All Customer Groups",
						"customer_territory": "All Territories",
						"customer_type": "Individual",
						"accounts": [{"company": company, "account": encode_company_abbr("Sundry Debtors", company)}],
						"company": company,
					}).insert().as_dict()
			elif party["party_type"] == "Supplier":
				if not frappe.db.exists({"doctype": "Supplier", "supplier_name": party["party_name"], "company": company}):
					frappe.get_doc({
						"doctype": "Supplier",
						"supplier_name": party["party_name"],
						"supplier_group": "All Supplier Groups",
						"supplier_type": "Individual",
						"accounts": [{"company": company, "account": encode_company_abbr("Sundry Creditors", company)}],
						"company": company,
					}).insert()
		except:
			traceback.print_exc()
			print(party)


def _create_items(items):
	for item in items:
		try:
			if not frappe.db.exists("Item", item["item_code"]):
				yield frappe.get_doc(item).insert().as_dict()
		except:
			traceback.print_exc()
			print(item)


def _create_vouchers(entries):
	for entry in entries:
		try:
			saved_entry = {
				"Journal Entry": create_journal_entry,
				"Sales Invoice": create_invoice,
				"Purchase Invoice": create_invoice,
			}[entry["doctype"]](entry)
			if saved_entry:
				yield saved_entry
		except:
			import traceback
			traceback.print_exc()


def create_journal_entry(voucher):
	try:
		if not frappe.db.exists({"doctype": "Journal Entry", "tally_id": voucher["tally_id"], "company": voucher["company"]}):
			for account in voucher["accounts"]:
				if account["is_party"]:
					if frappe.db.exists({"doctype": "Customer", "customer_name": account["account"], "company": voucher["company"]}):
						account["party_type"] = "Customer"
						account["party"] = account["account"]
						account["account"] = "Sundry Debtors"
					elif frappe.db.exists({"doctype": "Supplier", "supplier_name": account["account"], "company": voucher["company"]}):
						account["party_type"] = "Supplier"
						account["party"] = account["account"]
						account["account"] = "Sundry Creditors"
				account["account"] = encode_company_abbr(account["account"], voucher["company"])

			entry = frappe.get_doc(voucher).insert()
			entry.submit()
			return entry.as_dict()
		else:
			print("Already Exists : {}".format(voucher["tally_id"]))
	except:
		traceback.print_exc()
		print(voucher)


def create_invoice(voucher):
	try:
		if not frappe.db.exists({"doctype": voucher["doctype"], "tally_id": voucher["tally_id"], "company": voucher["company"]}):
			if voucher["doctype"] == "Sales Invoice":
				account_field = "income_account"
			elif voucher["doctype"] == "Purchase Invoice":
				account_field = "expense_account"

			for item in voucher["items"]:
				item[account_field] = encode_company_abbr(item[account_field], voucher["company"])

			for tax in voucher["taxes"]:
				tax["account_head"] = encode_company_abbr(tax["account_head"], voucher["company"])

			entry = frappe.get_doc(voucher).insert()
			entry.submit()
			return entry.as_dict()
		else:
			print("Already Exists : {}".format(voucher["tally_id"]))
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
def null():
	pass


@frappe.whitelist()
def clean_all():
	frappe.db.sql("""DELETE FROM `tabAccount`""")

	frappe.db.sql("""DELETE FROM `tabCustomer`""")
	frappe.db.sql("""DELETE FROM `tabSupplier`""")

	frappe.db.sql("""DELETE FROM `tabItem`""")
	frappe.db.sql("""DELETE FROM `tabItem Default`""")

	frappe.db.sql("""DELETE FROM `tabSales Invoice`""")
	frappe.db.sql("""DELETE FROM `tabSales Invoice Item`""")
	frappe.db.sql("""DELETE FROM `tabSales Taxes and Charges`""")

	frappe.db.sql("""DELETE FROM `tabPurchase Invoice`""")
	frappe.db.sql("""DELETE FROM `tabPurchase Invoice Item`""")
	frappe.db.sql("""DELETE FROM `tabPurchase Taxes and Charges`""")

	frappe.db.sql("""DELETE FROM `tabJournal Entry`""")
	frappe.db.sql("""DELETE FROM `tabJournal Entry Account`""")

	frappe.db.sql("""DELETE FROM `tabGL Entry`""")
	frappe.db.commit()

@frappe.whitelist()
def clean_entries():
	frappe.db.sql("""DELETE FROM `tabSales Invoice`""")
	frappe.db.sql("""DELETE FROM `tabSales Invoice Item`""")
	frappe.db.sql("""DELETE FROM `tabSales Taxes and Charges`""")

	frappe.db.sql("""DELETE FROM `tabPurchase Invoice`""")
	frappe.db.sql("""DELETE FROM `tabPurchase Invoice Item`""")
	frappe.db.sql("""DELETE FROM `tabPurchase Taxes and Charges`""")

	frappe.db.sql("""DELETE FROM `tabJournal Entry`""")
	frappe.db.sql("""DELETE FROM `tabJournal Entry Account`""")

	frappe.db.sql("""DELETE FROM `tabGL Entry`""")
	frappe.db.commit()
