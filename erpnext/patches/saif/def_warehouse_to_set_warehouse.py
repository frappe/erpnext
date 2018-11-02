# Copyright (c) 2018, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc("buying", "doctype", "purchase_order")
	frappe.reload_doc("selling", "doctype", "sales_order")
	frappe.reload_doc("stock", "doctype", "purchase_receipt")
	frappe.reload_doc("stock", "doctype", "delivery_note")
	frappe.reload_doc("accounts", "doctype", "purchase_invoice")
	frappe.reload_doc("accounts", "doctype", "sales_invoice")

	# Migrate clearance_date for only Bank and Cash accounts
	for dt in ['Sales Order', 'Delivery Note', 'Sales Invoice', 'Purchase Order', 'Purchase Receipt', 'Purchase Invoice']:
		frappe.db.sql("""update `tab{0}` set set_warehouse = def_warehouse""".format(dt))
