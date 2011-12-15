def execute():
	import webnotes
	webnotes.conn.sql("""\
		DELETE FROM `tabDefaultValue`
		WHERE parent='Control Panel' AND defkey='page_break'""")
