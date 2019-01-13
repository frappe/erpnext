# Copyright (c) 2018, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from erpnext.accounts.doctype.account.account import update_account_number, get_account_autoname

def execute():
	frappe.reload_doc("setup", "doctype", "company")

	companies = frappe.get_all("Company")
	goods_in_transit = {}
	for name in companies:
		doc = frappe.new_doc("Account")
		doc.company = name.name
		doc.account_name = "Goods in Transit"
		doc.parent_account = get_account_autoname(None, "Current Assets", name)
		doc.root_type = "Asset"
		doc.is_group = 1
		doc.save()
		goods_in_transit[name.name] = doc.name

	accounts = frappe.get_all("Account", {"account_name": "Letter of Credit Payable"})
	for name in accounts:
		doc = frappe.get_doc("Account", name)
		doc.parent_account = goods_in_transit[doc.company]
		doc.save()
		update_account_number(name.name, "Letters of Credit")

	for name in companies:
		doc = frappe.get_doc("Company", name)
		doc.set_default_accounts()
		doc.save()
