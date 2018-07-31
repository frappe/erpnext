# Copyright (c) 2018, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	'''

	Fields to move from the item to item defaults child table
	[ default_warehouse, buying_cost_center, expense_account, selling_cost_center, income_account ]

	'''
	if not frappe.db.has_column('Item', 'default_warehouse'):
		return

	frappe.reload_doc('stock', 'doctype', 'item_default')
	frappe.reload_doc('stock', 'doctype', 'item')

	if frappe.db.a_row_exists('Item Default'): return

	companies = frappe.get_all("Company")
	if len(companies) == 1:
		try:
			frappe.db.sql('''
					INSERT INTO `tabItem Default`
						(name, parent, parenttype, parentfield, idx, company, default_warehouse,
						buying_cost_center, selling_cost_center, expense_account, income_account, default_supplier)
					SELECT
						SUBSTRING(SHA2(name,224), 1, 10) as name, name as parent, 'Item' as parenttype,
						'item_defaults' as parentfield, 1 as idx, %s as company, default_warehouse,
						buying_cost_center, selling_cost_center, expense_account, income_account, default_supplier
					FROM `tabItem`;
			''', companies[0].name)
		except:
			pass
	else:
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

			for d in [
						["default_warehouse", "Warehouse"], ["expense_account", "Account"], ["income_account", "Account"],
						["buying_cost_center", "Cost Center"], ["selling_cost_center", "Cost Center"]
					]:
				if item.get(d[0]):
					company = frappe.get_value(d[1], item.get(d[0]), "company", cache=True)
					insert_into_item_defaults(d[0], item.get(d[0]), company)

			doc = frappe.get_doc("Item", item.name)
			doc.extend("item_defaults", item_defaults)

			for child_doc in doc.item_defaults:
				child_doc.db_insert()