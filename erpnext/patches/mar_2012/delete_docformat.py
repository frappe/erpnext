from __future__ import unicode_literals
def execute():
	import webnotes
	webnotes.conn.sql("DELETE FROM `tabDocField` WHERE options='DocFormat'")
	webnotes.conn.sql("DELETE FROM `tabDocField` WHERE parent='DocFormat'")
	webnotes.conn.sql("DELETE FROM `tabDocType` WHERE name='DocFormat'")
	webnotes.conn.commit()
	webnotes.conn.sql("DROP TABLE `tabDocFormat`")
	webnotes.conn.begin()
