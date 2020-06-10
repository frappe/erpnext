from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doctype('POS Profile')
	customer_group = frappe.db.get_single_value('Selling Settings', 'customer_group')
	if customer_group:
		frappe.db.sql(""" update `tabPOS Profile`
			set customer_group = %s where customer_group is null """, (customer_group))