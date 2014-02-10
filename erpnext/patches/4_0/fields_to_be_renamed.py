# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

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
	}

	from webnotes.model import rename_field
	
	for dt, field_list in rename_map.items():
		# reload doctype
		webnotes.reload_doc(webnotes.conn.get_value("DocType", dt, "module").lower(), 
			"doctype", dt.lower().replace(" ", "_"))
		
		# rename field
		for field in field_list:
			rename_field(dt, field[0], field[1])