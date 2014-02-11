# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.model import rename_field


def execute():
	rename_map = {
		"Quotation Item": [
			["ref_rate", "price_list_rate"], 
			["base_ref_rate", "base_price_list_rate"],
			["adj_rate", "discount_percentage"], 
			["export_rate", "rate"], 
			["basic_rate", "base_rate"], 
			["amount", "base_amount"], 
			["export_amount", "amount"]
		],
		
		"Sales Order Item": [
			["ref_rate", "price_list_rate"], 
			["base_ref_rate", "base_price_list_rate"],
			["adj_rate", "discount_percentage"], 
			["export_rate", "rate"], 
			["basic_rate", "base_rate"], 
			["amount", "base_amount"], 
			["export_amount", "amount"], 
			["reserved_warehouse", "warehouse"]
		],
		
		"Delivery Note Item": [
			["ref_rate", "price_list_rate"], 
			["base_ref_rate", "base_price_list_rate"], 
			["adj_rate", "discount_percentage"], 
			["export_rate", "rate"], 
			["basic_rate", "base_rate"], 
			["amount", "base_amount"], 
			["export_amount", "amount"]
		],

		"Sales Invoice Item": [
			["ref_rate", "price_list_rate"], 
			["base_ref_rate", "base_price_list_rate"], 
			["adj_rate", "discount_percentage"], 
			["export_rate", "rate"], 
			["basic_rate", "base_rate"], 
			["amount", "base_amount"], 
			["export_amount", "amount"]
		],

		"Supplier Quotation Item": [
			["import_ref_rate", "price_list_rate"], 
			["purchase_ref_rate", "base_price_list_rate"], 
			["discount_rate", "discount_percentage"], 
			["import_rate", "rate"], 
			["purchase_rate", "base_rate"], 
			["amount", "base_amount"], 
			["import_amount", "amount"]
		],
	
		"Purchase Order Item": [
			["import_ref_rate", "price_list_rate"], 
			["purchase_ref_rate", "base_price_list_rate"], 
			["discount_rate", "discount_percentage"], 
			["import_rate", "rate"], 
			["purchase_rate", "base_rate"], 
			["amount", "base_amount"], 
			["import_amount", "amount"]
		],
	
		"Purchase Receipt Item": [
			["import_ref_rate", "price_list_rate"], 
			["purchase_ref_rate", "base_price_list_rate"], 
			["discount_rate", "discount_percentage"], 
			["import_rate", "rate"], 
			["purchase_rate", "base_rate"], 
			["amount", "base_amount"], 
			["import_amount", "amount"]
		],
		
		"Purchase Invoice Item": [
			["import_ref_rate", "price_list_rate"], 
			["purchase_ref_rate", "base_price_list_rate"], 
			["discount_rate", "discount_percentage"], 
			["import_rate", "rate"], 
			["rate", "base_rate"], 
			["amount", "base_amount"], 
			["import_amount", "amount"], 
			["expense_head", "expense_account"]
		],
		
		"Item": [
			["purchase_account", "expense_account"],
			["default_sales_cost_center", "selling_cost_center"],
			["cost_center", "buying_cost_center"]
		],
		"Item Price": [
			["ref_rate", "price_list_rate"]
		]
	}

	reload_docs(rename_map)
	
	for dt, field_list in rename_map.items():
		for field in field_list:
			rename_field(dt, field[0], field[1])
			
def reload_docs(docs):
	for dn in docs:
		module = webnotes.conn.get_value("DocType", dn, "module").lower().replace(" ", "_")
		webnotes.reload_doc(module,	"doctype", dn.lower().replace(" ", "_"))
	
	# reload all standard print formats
	for pf in webnotes.conn.sql("""select name, module from `tabPrint Format` 
			where ifnull(standard, 'No') = 'Yes'""", as_dict=1):
		webnotes.reload_doc(pf.module, "Print Format", pf.name)
		
	# reload all standard reports
	for r in webnotes.conn.sql("""select name, module from `tabReport` 
		where ifnull(is_standard, 'No') = 'Yes'
		and report_type in ('Report Builder', 'Query Report')""", as_dict=1):
			webnotes.reload_doc(r.module, "Report", r.name)