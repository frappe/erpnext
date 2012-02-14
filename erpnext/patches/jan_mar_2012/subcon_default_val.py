def execute():
	import webnotes
	webnotes.conn.sql("""
		update `tabDocField` set `default` = 'No' 
		where parent in ('Purchase Order', 'Purchase Receipt') 
		and fieldname = 'is_subcontracted'
	""")
