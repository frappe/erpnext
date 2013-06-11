def execute():
	import webnotes
	try:
		for mapper in webnotes.conn.sql("""select name from `tabGL Mapper`"""):
			webnotes.delete_doc("GL Mapper", mapper[0])
	except Exception, e:
		pass