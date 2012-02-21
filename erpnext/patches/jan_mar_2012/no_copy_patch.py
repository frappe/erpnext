def execute():
	import webnotes
	webnotes.conn.sql("update `tabDocField` set no_copy = 1 where fieldname = 'insert_after' and parent = 'Custom Field'")
