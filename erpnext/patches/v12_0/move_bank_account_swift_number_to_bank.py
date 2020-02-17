from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc('accounts', 'doctype', 'bank', force=1)

	banks = frappe.get_all('Bank', 'name')
	for bank in banks:
		bank_accounts = frappe.get_all('Bank Account', filters={'bank': bank.name}, fields=['swift_number', 'branch_code'])
		bank_account = ''
		if len(bank_accounts):
			bank_account = bank_accounts[0]
			if bank_account and bank_account.swift_number:
				bank.swift_number = bank_account.swift_number
			if bank_account and bank_account.branch_code:
				bank.branch_code = bank_account.branch_code
			bank.save()

	frappe.reload_doc('accounts', 'doctype', 'bank_account')
	frappe.reload_doc('accounts', 'doctype', 'payment_request')