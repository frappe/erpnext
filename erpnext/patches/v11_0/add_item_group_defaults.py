# Copyright (c) 2018, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	'''

	Fields to move from item group to item defaults child table
	[ default_cost_center, default_expense_account, default_income_account ]

	'''

	frappe.reload_doc('stock', 'doctype', 'item_default')
	frappe.reload_doc('setup', 'doctype', 'item_group')

	companies = frappe.get_all("Company")
	item_groups = frappe.db.sql("""select name, default_income_account, default_expense_account,\
		default_cost_center from `tabItem Group`""", as_dict=True)

	if len(companies) == 1:
		for item_group in item_groups:
			doc = frappe.get_doc("Item Group", item_group.get("name"))
			item_group_defaults = []
			item_group_defaults.append({
				"company": companies[0].name,
				"income_account": item_group.get("default_income_account"),
				"expense_account": item_group.get("default_expense_account"),
				"buying_cost_center": item_group.get("default_cost_center"),
				"selling_cost_center": item_group.get("default_cost_center")
			})
			doc.extend("item_group_defaults", item_group_defaults)
			for child_doc in doc.item_group_defaults:
				child_doc.db_insert()
	else:
		item_group_dict = {
			"default_expense_account": ["expense_account"],
			"default_income_account": ["income_account"],
			"default_cost_center": ["buying_cost_center", "selling_cost_center"]
		}
		for item_group in item_groups:
			item_group_defaults = []
			def insert_into_item_defaults(doc_field_name, doc_field_value, company):
				for d in item_group_defaults:
					if d.get("company") == company:
						d[doc_field_name[0]] = doc_field_value
						if len(doc_field_name) > 1:
							d[doc_field_name[1]] = doc_field_value
						return

				item_group_defaults.append({
					"company": company,
					doc_field_name[0]: doc_field_value
				})

				if(len(doc_field_name) > 1):
					item_group_defaults[len(item_group_defaults)-1][doc_field_name[1]] = doc_field_value

			for d in [
					["default_expense_account", "Account"], ["default_income_account", "Account"],
					["default_cost_center", "Cost Center"]
				]:
				if item_group.get(d[0]):
					company = frappe.get_value(d[1], item_group.get(d[0]), "company", cache=True)
					doc_field_name = item_group_dict.get(d[0])

					insert_into_item_defaults(doc_field_name, item_group.get(d[0]), company)

			doc = frappe.get_doc("Item Group", item_group.get("name"))
			doc.extend("item_group_defaults", item_group_defaults)
			for child_doc in doc.item_group_defaults:
				child_doc.db_insert()
