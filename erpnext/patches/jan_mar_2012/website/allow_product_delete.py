def execute():
	"""
		Allow deletion of products
	"""
	import webnotes
	webnotes.conn.sql("""UPDATE `tabDocPerm` SET cancel=1
		WHERE parent='Product' AND role='Website Manager'""")
