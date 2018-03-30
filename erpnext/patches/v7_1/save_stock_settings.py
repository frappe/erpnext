from __future__ import unicode_literals
import frappe

def execute():
	stock_settings = frappe.get_doc('Stock Settings')
	
	if stock_settings.default_warehouse \
		and not frappe.db.exists("Warehouse", stock_settings.default_warehouse):
			stock_settings.default_warehouse = None
			
	if stock_settings.stock_uom and not frappe.db.exists("UOM", stock_settings.stock_uom):
		stock_settings.stock_uom = None
		
	stock_settings.flags.ignore_mandatory = True
	stock_settings.save()
