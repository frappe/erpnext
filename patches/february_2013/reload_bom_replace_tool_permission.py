def execute():
	import webnotes
	webnotes.conn.sql("""delete from `tabDocPerm` where parent = 'BOM Replace Tool'""")
	webnotes.reload_doc("manufacturing", "doctype", "bom_replace_tool")