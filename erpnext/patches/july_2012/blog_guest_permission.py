def execute():
	"""allocate read write permission to guest for doctype 'Blog'"""
	import webnotes
	webnotes.conn.sql("""delete from `tabDocPerm` where parent = 'Blog'""")
	
	webnotes.conn.commit()
	
	import webnotes.model.sync
	webnotes.model.sync.sync('website', 'blog', 1)

	webnotes.conn.begin()
