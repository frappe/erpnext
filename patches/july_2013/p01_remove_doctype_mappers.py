import webnotes
def execute():
	for m in webnotes.conn.sql("select name from `tabDocType Mapper`"):
		webnotes.delete_doc("DocType Mapper", m[0])