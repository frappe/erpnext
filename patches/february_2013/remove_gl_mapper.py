def execute():
	import webnotes
	from webnotes.model.doc import delete_doc
	for mapper in webnotes.conn.sql("""select name from `tabGL Mapper`"""):
		delete_doc("GL Mapper", mapper[0])