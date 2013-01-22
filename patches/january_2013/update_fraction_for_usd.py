def execute():
	import webnotes
	webnotes.conn.sql("""update `tabCurrency` set fraction = 'Cent' where fraction = 'Cent[D]'""")