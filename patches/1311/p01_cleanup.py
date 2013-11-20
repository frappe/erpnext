# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():
	webnotes.reload_doc("stock", "doctype", "material_request")
	webnotes.reload_doc("buying", "doctype", "purchase_order")
	webnotes.reload_doc("selling", "doctype", "lead")

	from core.doctype.custom_field.custom_field import create_custom_field_if_values_exist
	
	create_custom_field_if_values_exist("Material Request", 
		{"fieldtype":"Text", "fieldname":"remark", "label":"Remarks","insert_after":"Fiscal Year"})
	create_custom_field_if_values_exist("Purchase Order", 
		{"fieldtype":"Text", "fieldname":"instructions", "label":"Instructions","insert_after":"% Billed"})		
	create_custom_field_if_values_exist("Purchase Order", 
		{"fieldtype":"Text", "fieldname":"remarks", "label":"Remarks","insert_after":"% Billed"})
	create_custom_field_if_values_exist("Purchase Order", 
		{"fieldtype":"Text", "fieldname":"payment_terms", "label":"Payment Terms","insert_after":"Print Heading"})		
	create_custom_field_if_values_exist("Lead", 
		{"fieldtype":"Text", "fieldname":"remark", "label":"Remark","insert_after":"Territory"})
		