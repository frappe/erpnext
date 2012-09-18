from __future__ import unicode_literals
def execute():
	import webnotes
	from webnotes.model import delete_doc
	delete_doc('DocType', 'Bulk Rename Tool')
	webnotes.conn.commit()
	webnotes.conn.sql("drop table `tabBulk Rename Tool`")
	webnotes.conn.begin()