# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	sales_orders = frappe.db.sql("""select name from `tabSales Order` 
		where docstatus = 1 and ifnull(is_recurring, 0) = 1 
		and (per_delivered > 0 or per_billed > 0)""", as_dict=1)

	for so in sales_orders:
		if not frappe.db.exists("Delivery Note Item", {"against_sales_order": so.name, "docstatus": 1}):
			frappe.db.sql("""update `tabSales Order` set per_delivered = 0, 
				delivery_status = 'Not Delivered' where name = %s""", so.name)
			frappe.db.sql("""update `tabSales Order Item` set delivered_qty = 0
				where parent = %s""", so.name)

		if not frappe.db.exists("Sales Invoice Item", {"sales_order": so.name, "docstatus": 1}):
			frappe.db.sql("""update `tabSales Order` set per_billed = 0, 
				billing_status = 'Not Billed' where name = %s""", so.name)
			frappe.db.sql("""update `tabSales Order Item` set billed_amt = 0
				where parent = %s""", so.name)

	purchase_orders = frappe.db.sql("""select name from `tabPurchase Order` 
		where docstatus = 1 and ifnull(is_recurring, 0) = 1 
		and (per_received > 0 or per_billed > 0)""", as_dict=1)

	for po in purchase_orders:
		if not frappe.db.exists("Purchase Receipt Item", {"prevdoc_doctype": "Purchase Order", 
			"prevdoc_docname": po.name, "docstatus": 1}):
				frappe.db.sql("""update `tabPurchase Order` set per_received = 0
					where name = %s""", po.name)
				frappe.db.sql("""update `tabPurchase Order Item` set received_qty = 0
					where parent = %s""", po.name)

		if not frappe.db.exists("Purchase Invoice Item", {"purchase_order": po.name, "docstatus": 1}):
			frappe.db.sql("""update `tabPurchase Order` set per_billed = 0
				where name = %s""", po.name)
			frappe.db.sql("""update `tabPurchase Order Item` set billed_amt = 0
				where parent = %s""", po.name)