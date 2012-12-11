import webnotes
def execute():
	webnotes.conn.sql("""update `tabDocType` set default_print_format=null
		where default_print_format='Standard'""")