def execute():
	import webnotes
	webnotes.conn.sql("""
		DELETE FROM tabDocField
		WHERE parent = 'Email Digest'
		AND label = 'Add Recipients'
		AND fieldtype = 'Button'""")

