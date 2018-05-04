# Copyright (c) 2018, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	'''

	Fields to move from the item to item defaults child table
	[ default_warehouse, buying_cost_center, expense_account, selling_cost_center, income_account ]

	'''

	frappe.reload_doc('stock', 'doctype', 'item_default')
	frappe.reload_doc('stock', 'doctype', 'item')

	item_details = frappe.get_all("Item", fields=["name", "default_warehouse", "buying_cost_center",
								"expense_account", "selling_cost_center", "income_account"], limit=100)

	for item in item_details:
		item_defaults = []

		def insert_into_item_defaults(doc_field_name, doc_field_value, company):
			for d in item_defaults:
				if d.get("company") == company:
					d[doc_field_name] = doc_field_value
					return
			item_defaults.append({
				"company": company,
				doc_field_name: doc_field_value
			})

		if item.default_warehouse:
			default_warehouse_company = frappe.get_value("Warehouse", item.default_warehouse, "company", cache=True)
			insert_into_item_defaults("default_warehouse", item.default_warehouse, default_warehouse_company)

		if item.buying_cost_center:
			buying_cost_center_company = get_cost_center_company(item.buying_cost_center)
			insert_into_item_defaults("buying_cost_center", item.buying_cost_center, buying_cost_center_company)

		if item.selling_cost_center:
			selling_cost_center_company = get_cost_center_company(item.buying_cost_center)
			insert_into_item_defaults("selling_cost_center", item.selling_cost_center, selling_cost_center_company)

		if item.expense_account:
			expense_account_company = get_account_company(item.expense_account)
			insert_into_item_defaults("expense_account", item.expense_account, expense_account_company)

		if item.income_account:
			income_account_company = get_account_company(item.income_account)
			insert_into_item_defaults("income_account", item.income_account, income_account_company)

		doc = frappe.get_doc("Item", item.name)
		doc.extend("item_defaults", item_defaults)
		
		for child_doc in doc.item_defaults:
			child_doc.db_update()

def get_account_company(account_name):
	return frappe.get_value("Account", account_name, "company", cache=True)

def get_cost_center_company(cost_center):
	return frappe.get_value("Cost Center", cost_center, "company", cache=True)
