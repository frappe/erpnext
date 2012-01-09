import webnotes
def execute():
	"""
		Mark DocType Profile as 'not_in_create'
	"""
	webnotes.conn.sql("""
		UPDATE `tabDocType`
		SET in_create=1
		WHERE name='Profile'
	""")
