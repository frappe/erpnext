from __future__ import unicode_literals
def execute():
	"""allocate read write permission to guest for doctype 'Blog'"""
	import webnotes
	webnotes.conn.sql("""delete from `tabDocPerm` where parent = 'Blog'""")
	
	webnotes.conn.commit()
	
	webnotes.reload_doc('website', 'doctype', 'blog')

	webnotes.conn.begin()
