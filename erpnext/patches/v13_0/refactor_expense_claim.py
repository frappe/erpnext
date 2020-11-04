# Copyright (c) 2020, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.utils.rename_field import rename_field

def execute():
	if frappe.db.has_table('Expense Claim Type') and frappe.db.has_table('Expense Claim Account'):
		# make items from Expense Claim Type
		expense_types = frappe.get_all('Expense Claim Type',
			fields = ['name', 'deferred_expense_account', 'expense_type', 'description']
		)

		for entry in expense_types:
			doc = frappe.get_doc('Expense Claim Type', entry.name)

			item = frappe.new_doc('Item')
			item.item_code = doc.expense_type
			item.item_group = 'Services'
			item.is_stock_item = 0
			item.decription = doc.description
			item.include_item_in_manufacturing = 0
			item.stock_uom = 'Nos'
			item.enable_deferred_expense = doc.deferred_expense_account

			for acc in doc.accounts:
				item.append('item_defaults', {
					'company': acc.company,
					'expense_account': acc.default_account
				})

			item.save()

		rename_field('Expense Claim Detail', 'expense_item', 'item_code')
		rename_field('Expense Claim Detail', 'amount', 'claimed_amount')
		rename_field('Expense Claim Detail', 'sanctioned_amount', 'amount')
		frappe.db.sql("""
			UPDATE `tabExpense Claim Detail`
			SET parentfield='items'
			WHERE parentfield='expenses'"""
		)

		frappe.reload_doc('hr', 'doctype', 'expense_claim_detail')
		frappe.reload_doc('hr', 'doctype', 'expense_claim')

		frappe.db.sql("""DELETE from `tabExpense Claim Account`""")
		frappe.db.sql("""DELETE from `tabExpense Claim Type`""")
		frappe.delete_doc_if_exists('DocType', 'Expense Claim Account')
		frappe.delete_doc_if_exists('DocType', 'Expense Claim Type')