from __future__ import unicode_literals
def execute():
	import webnotes
	webnotes.conn.sql("""\
		delete from `tabDocPerm`
		where parent in ('Address', 'Contact')""")
	webnotes.conn.commit()
	
	import webnotes.model.sync
	webnotes.model.sync.sync('utilities', 'address')
	webnotes.model.sync.sync('utilities', 'contact')
	webnotes.conn.begin()