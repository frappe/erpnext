def execute():
	import webnotes
	webnotes.conn.sql("update `tabDocPerm` set permlevel = 0 where parent = 'Bin'")