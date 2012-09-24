from __future__ import unicode_literals
def execute():
	import webnotes
	from webnotes.model import delete_doc
	webnotes.conn.sql("update `tabDocType` set module = 'Utilities' where name in ('Question', 'Answer')")
	delete_doc('Module Def', 'Knowledge Base')
