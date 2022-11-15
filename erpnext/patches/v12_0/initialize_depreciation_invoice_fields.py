# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

def execute():
	frappe.reload_doc('accounts', 'doctype', 'sales_invoice')
	frappe.reload_doc('accounts', 'doctype', 'sales_invoice_item')
	frappe.db.sql("update `tabSales Invoice Item` set amount_before_depreciation = amount_before_discount")
	frappe.db.sql("update `tabSales Invoice` set total_before_depreciation = total_before_discount")
