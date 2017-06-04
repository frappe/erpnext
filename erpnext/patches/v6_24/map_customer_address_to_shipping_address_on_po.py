# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doctype("Purchase Order")
	
	if not frappe.db.has_column("Purchase Order", "shipping_address"):
		return
		
	if not frappe.db.has_column("Purchase Order", "customer_address"):
		return
	
	frappe.db.sql("""update `tabPurchase Order` set shipping_address=customer_address, 
		shipping_address_display=customer_address_display""")
	
	frappe.db.commit()