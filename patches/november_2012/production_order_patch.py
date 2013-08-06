# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

def execute():
	import webnotes
	
	webnotes.reload_doc("manufacturing", "doctype", "production_order")
	webnotes.reload_doc("stock", "doctype", "stock_entry")
	
	webnotes.conn.sql("""update `tabStock Entry` 
		set use_multi_level_bom = if(consider_sa_items_as_raw_materials='Yes', 0, 1)""")
	
	webnotes.conn.sql("""update `tabProduction Order` 
		set use_multi_level_bom = if(consider_sa_items='Yes', 0, 1)
		where use_multi_level_bom is null""")
