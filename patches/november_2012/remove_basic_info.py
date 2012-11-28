def execute():
	import webnotes	
	webnotes.conn.sql("""delete from `tabDocField` 
			where label = 'Basic Info' and fieldtype = 'Section Break'""")