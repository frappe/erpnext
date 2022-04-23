# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	if frappe.db.table_exists("POS Closing Voucher"):
		if not frappe.db.exists("DocType", "POS Closing Entry"):
			frappe.rename_doc('DocType', 'POS Closing Voucher', 'POS Closing Entry', force=True)
		
		if not frappe.db.exists('DocType', 'POS Closing Entry Taxes'):
			frappe.rename_doc('DocType', 'POS Closing Voucher Taxes', 'POS Closing Entry Taxes', force=True)
		
		if not frappe.db.exists('DocType', 'POS Closing Voucher Details'):
			frappe.rename_doc('DocType', 'POS Closing Voucher Details', 'POS Closing Entry Detail', force=True)

		frappe.reload_doc('Accounts', 'doctype', 'POS Closing Entry')
		frappe.reload_doc('Accounts', 'doctype', 'POS Closing Entry Taxes')
		frappe.reload_doc('Accounts', 'doctype', 'POS Closing Entry Detail')

	if frappe.db.exists("DocType", "POS Closing Voucher"):
		frappe.delete_doc("DocType", "POS Closing Voucher")
		frappe.delete_doc("DocType", "POS Closing Voucher Taxes")
		frappe.delete_doc("DocType", "POS Closing Voucher Details")
		frappe.delete_doc("DocType", "POS Closing Voucher Invoices")