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
	frappe.flags.in_migrate = True
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
	frappe.flags.in_migrate = True
	parties = json.loads(parties)
	make_custom_fields(["Customer", "Supplier"], "company")
	saved_parties = list(_create_parties(company, parties))
	frappe.db.commit()
	frappe.clear_messages()
	return saved_parties


@frappe.whitelist()
def create_items(company, items):
	frappe.flags.in_migrate = True
	items = json.loads(items)
	make_custom_fields(["Item"], "company", "Link", "Company")
	saved_items = list(_create_items(items))
	frappe.db.commit()
	frappe.clear_messages()
	return saved_items

@frappe.whitelist()
def create_vouchers(company, vouchers):
	vouchers = json.loads(vouchers)
	make_custom_fields(["Journal Entry", "Purchase Invoice", "Sales Invoice"], "tally_id")
	frappe.enqueue(method="erpnext.erpnext_integrations.tally_migration._create_vouchers", timeout=3600, **{"entries": vouchers})
	frappe.db.commit()
	frappe.clear_messages()


def log(title="Some Error", data="Some Data"):
	import json, traceback
	traceback.print_exc()
	frappe.log_error(title=title,
		message="\n".join([
			"Data",
			json.dumps(data,
				sort_keys=True,
				indent=4,
				separators=(',', ': ')
			),
			"Exception",
			traceback.format_exc()
		])
	)
	frappe.db.commit()

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
			log(title="Root Account Error", data=[account, account_name, root_type])


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
			log(title="Account Error", data=[account, account_name, account_type])


def make_custom_fields(doctypes, field_name="tally_id", field_type="Data", options=None):
	for doctype in doctypes:
		if not frappe.db.exists({"doctype": "Custom Field", "dt": doctype, "fieldname": field_name}):
			frappe.get_doc({
				"doctype": "Custom Field",
				"label": "Tally ID",
				"dt": doctype,
				"fieldname": field_name,
				"fieldtype": field_type,
				"options": options,
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
			log(title="Party Error", data=party)


def _create_items(items):
	for item in items:
		try:
			if not frappe.db.exists("Item", item["item_code"]):
				yield frappe.get_doc(item).insert().as_dict()
		except:
			log(title="Item Error", data=item)


def _create_vouchers(entries):
	try:
		frappe.flags.in_migrate = True
		entries = filter_entries(entries)
		for entry in entries:
			try:
				{
					"Journal Entry": create_journal_entry,
					"Sales Invoice": create_invoice,
					"Purchase Invoice": create_invoice,
				}[entry["doctype"]](entry)
				frappe.db.commit()
			except:
				log(title="Voucher Error", data=entry)
	except:
		import traceback
		traceback.print_exc()


def filter_entries(entries):
	queries = {}
	for entry in entries:
		queries.setdefault(entry["doctype"], []).append(entry["tally_id"])

	existing_ids = set()
	for doctype, tally_ids in queries.items():
		existing_ids.update(frappe.get_all(doctype,
			fields=["tally_id"],
			filters={
				"tally_id": ("in", tally_ids),
				"company": entries[0]["company"]
			}
		))

	entries = list(filter(lambda e: e["tally_id"] not in existing_ids, entries))
	return entries


def create_journal_entry(voucher):
	try:
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
	except:
		log(title="JE Error", data=voucher)


def create_invoice(voucher):
	try:
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
	except:
		log(title="Invoice Error", data=voucher)


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
