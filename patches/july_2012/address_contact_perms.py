from __future__ import unicode_literals
def execute():
	import webnotes
	webnotes.conn.sql("""\
		delete from `tabDocPerm`
		where parent in ('Address', 'Contact')""")
	webnotes.conn.commit()
	
	webnotes.reload_doc('utilities', 'doctype', 'address')
	webnotes.reload_doc('utilities', 'doctype', 'contact')
	webnotes.conn.begin()