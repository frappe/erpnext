def execute():
	import webnotes
	for mapper in webnotes.conn.sql("""select name from `tabGL Mapper`"""):
		webnotes.delete_doc("GL Mapper", mapper[0])