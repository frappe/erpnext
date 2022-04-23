from __future__ import unicode_literals
import frappe

def execute():
	frappe.rename_doc('DocType', 'Account Type', 'Bank Account Type', force=True)
	frappe.rename_doc('DocType', 'Account Subtype', 'Bank Account Subtype', force=True)
	frappe.reload_doc('accounts', 'doctype', 'bank_account')