# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

def execute():
	from webnotes.modules.import_file import import_files
	import_files([["selling", "Print Format", "Quotation Classic"], 
		["selling", "Print Format", "Quotation Modern"], 
		["selling", "Print Format", "Quotation Spartan"], 
		["selling", "Print Format", "Sales Order Classic"], 
		["selling", "Print Format", "Sales Order Modern"], 
		["selling", "Print Format", "Sales Order Spartan"]])
		
	import_files([["stock", "Print Format", "Delivery Note Classic"], 
		["stock", "Print Format", "Delivery Note Modern"], 
		["stock", "Print Format", "Delivery Note Spartan"]])
		
	import_files([["accounts", "Print Format", "Sales Invoice Classic"], 
		["accounts", "Print Format", "Sales Invoice Modern"], 
		["accounts", "Print Format", "Sales Invoice Spartan"]])