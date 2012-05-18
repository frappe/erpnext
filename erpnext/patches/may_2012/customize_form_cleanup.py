def execute():
	import webnotes
	webnotes.conn.sql("delete from `tabCustomize Form Field`")
	webnotes.conn.sql("""delete from `tabSingles`
		where doctype='Customize Form'""")