from __future__ import unicode_literals
import frappe
from erpnext.stock.stock_balance import repost_stock

def execute():
	frappe.reload_doc('manufacturing', 'doctype', 'production_order_item')
	frappe.reload_doc('manufacturing', 'doctype', 'production_order')
	
	modified_items = frappe.db.sql_list("""
		select name from `tabItem` 
		where is_stock_item=1 and modified >= '2016-10-31'
	""")
	
	if not modified_items:
		return
	
	item_warehouses_with_transactions = []
	transactions = ("Sales Order Item", "Material Request Item", "Purchase Order Item", 
		"Stock Ledger Entry", "Packed Item")
	
	for doctype in transactions:
		item_warehouses_with_transactions += list(frappe.db.sql("""
			select distinct item_code, warehouse
			from `tab{0}` where docstatus=1 and item_code in ({1})"""
			.format(doctype, ', '.join(['%s']*len(modified_items))), tuple(modified_items)))
			
	item_warehouses_with_transactions += list(frappe.db.sql("""
		select distinct production_item, fg_warehouse 
		from `tabProduction Order` where docstatus=1 and production_item in ({0})"""
		.format(', '.join(['%s']*len(modified_items))), tuple(modified_items)))
	
	item_warehouses_with_transactions += list(frappe.db.sql("""
		select distinct pr_item.item_code, pr.source_warehouse 
		from `tabProduction Order` pr, `tabProduction Order Item` pr_item 
		where pr_item.parent and pr.name and pr.docstatus=1 and pr_item.item_code in ({0})"""
		.format(', '.join(['%s']*len(modified_items))), tuple(modified_items)))
	
	item_warehouses_with_bin = list(frappe.db.sql("select distinct item_code, warehouse from `tabBin`"))
	
	item_warehouses_with_missing_bin = list(
		set(item_warehouses_with_transactions) - set(item_warehouses_with_bin))	
	
	for item_code, warehouse in item_warehouses_with_missing_bin:
		repost_stock(item_code, warehouse)
