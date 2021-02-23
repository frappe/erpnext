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
			item = frappe.new_doc('Item')
			item.item_code = entry.expense_type
			item.item_group = 'Services'
			item.is_stock_item = 0
			item.decription = entry.description
			item.include_item_in_manufacturing = 0
			item.stock_uom = 'Nos'
			item.enable_deferred_expense = entry.deferred_expense_account

			accounts = frappe.db.get_all('Expense Claim Account', filters={
				'parent': entry.name
			}, fields=['company', 'default_account'])

			for acc in accounts:
				item.append('item_defaults', {
					'company': acc.company,
					'expense_account': acc.default_account
				})

			item.save()

		frappe.rename_doc('DocType', 'Expense Claim Detail', 'Expense Claim Item', force=True)
		rename_field('Expense Claim Item', 'expense_item', 'item_code')
		rename_field('Expense Claim Item', 'amount', 'claimed_amount')
		rename_field('Expense Claim Item', 'sanctioned_amount', 'amount')
		rename_field('Expense Claim', 'total_sanctioned_amount', 'total_amount')
		frappe.db.sql("""
			UPDATE `tabExpense Claim Item`
			SET parentfield='items'
			WHERE parentfield='expenses'"""
		)

		frappe.reload_doc('hr', 'doctype', 'expense_claim')

		frappe.db.sql("""DELETE from `tabExpense Claim Account`""")
		frappe.db.sql("""DELETE from `tabExpense Claim Type`""")
		frappe.delete_doc_if_exists('DocType', 'Expense Claim Account')
		frappe.delete_doc_if_exists('DocType', 'Expense Claim Type')

	# copy taxes and charges (Expense Taxes and Charges -> Purchase Taxes and Charges)
		expense_taxes = frappe.db.get_all('Expense Taxes and Charges',
			fields=['account_head', 'description', 'rate', 'cost_center', 'tax_amount', 'total', 'parent'])

		data = []
		for entry in expense_taxes:
			data.append((
				frappe.generate_hash("", 10), # name
				'Total', # category
				'Add', # add_deduct_tax
				'On Net Total', # charge_type
				data.get('account_head'),
				data.get('description'),
				data.get('rate'),
				data.get('cost_center'),
				data.get('tax_amount'), # tax_amount
				data.get('tax_amount'), # base_tax_amount,
				data.get('tax_amount'), # tax_amount_after_discount_amount
				data.get('tax_amount'), # base_tax_amount_after_discount_amount
				data.get('total'), # total
				data.get('total'), # base_total
				data.get('parent'),
				'Expense Claim'
			))

		if data:
			frappe.db.sql('''
				INSERT INTO `tabPurchase Taxes and Charges`
				(
					`name`, `category`, `add_deduct_tax`, `charge_type`, `account_head`, `description`,
					`rate`, `cost_center`, `tax_amount`, `base_tax_amount`, `tax_amount_after_discount_amount`,
					`base_tax_amount_after_discount_amount`, `total`, `base_total`, `parent`, `parenttype`
				)
				VALUES {}
			'''.format(', '.join(['%s'] * len(data))), tuple(data))

	doctype_list = ['Expense Claim Item', 'Expense Claim Advance', 'Expense Claim']

	for dt in doctype_list:
		frappe.reload_doc('HR', 'doctype', dt)

	# get all companies and their currency
	all_companies = frappe.db.get_all("Company", fields=["name", "default_currency"])
	for d in all_companies:
		company = d.name
		company_currency = d.default_currency

		# update fields in Expense Claim along with grand total and outstanding amount
		frappe.db.sql("""
			update `tabExpense Claim`
			set currency = %s,
				conversion_rate = 1,
				taxes_and_charges_added = total_taxes_and_charges,
				base_total_claimed_amount = total_claimed_amount,
				base_total = total,
				base_grand_total = grand_total,
				base_total_amount_reimbursed = total_amount_reimbursed,
				base_taxes_and_charges_added = total_taxes_and_charges,
				base_taxes_and_charges_deducted = 0.0,
				base_total_taxes_and_charges = total_taxes_and_charges
			where company=%s
		""", (company_currency, company))