def execute():
	import webnotes
	webnotes.conn.sql("""update `tabProduction Order` 
		set use_multi_level_bom = if(consider_sa_items='Yes', 0, 1)""")
		
	webnotes.conn.sql("""update `tabStock Entry` 
		set use_multi_level_bom = if(consider_sa_items_as_raw_materials='Yes', 0, 1)""")
	