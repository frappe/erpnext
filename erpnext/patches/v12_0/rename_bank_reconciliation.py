# Copyright (c) 2018, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	if frappe.db.table_exists("Bank Reconciliation"):
		frappe.rename_doc('DocType', 'Bank Reconciliation', 'Bank Clearance', force=True)
		frappe.reload_doc('Accounts', 'doctype', 'Bank Clearance')

		frappe.rename_doc('DocType', 'Bank Reconciliation Detail', 'Bank Clearance Detail', force=True)
		frappe.reload_doc('Accounts', 'doctype', 'Bank Clearance Detail')
