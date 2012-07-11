def execute():
	import webnotes
	webnotes.conn.sql("""update tabAccount set freeze_account='No' where freeze_account is null""")
