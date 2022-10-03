# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt


import frappe


def execute():

	if frappe.db.exists("DocType", "Bank Reconciliation Detail") and frappe.db.exists(
		"DocType", "Bank Clearance Detail"
	):

		frappe.delete_doc("DocType", "Bank Reconciliation Detail", force=1)
