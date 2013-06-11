from __future__ import unicode_literals
def execute():
	"""allow read permission to all for report list"""
	import webnotes
	webnotes.conn.sql("""\
		delete from `tabDocPerm`
		where parent in ('Report', 'Search Criteria')""")
	
	webnotes.reload_doc('core', 'doctype', 'report')
