from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc('accounts', 'doctype', 'bank', force=1)

	if frappe.db.table_exists('Bank') and frappe.db.table_exists('Bank Account'):
		frappe.db.sql("""
			UPDATE `tabBank` b, `tabBank Account` ba
			SET b.swift_number = ba.swift_number, b.branch_code = ba.branch_code
			WHERE b.name = ba.bank
		""")

	frappe.reload_doc('accounts', 'doctype', 'bank_account')
	frappe.reload_doc('accounts', 'doctype', 'payment_request')