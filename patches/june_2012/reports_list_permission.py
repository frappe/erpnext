from __future__ import unicode_literals
def execute():
	"""allow read permission to all for report list"""
	import webnotes
	webnotes.conn.sql("""\
		delete from `tabDocPerm`
		where parent in ('Report', 'Search Criteria')""")
	
	webnotes.conn.commit()
	
	import webnotes.model.sync
	webnotes.model.sync.sync('core', 'search_criteria')
	webnotes.model.sync.sync('core', 'report')

	webnotes.conn.begin()