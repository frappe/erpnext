from __future__ import unicode_literals
def execute():
	import webnotes
	webnotes.conn.commit()
	webnotes.conn.sql("alter table `tabSessions` modify user varchar(180)")
	webnotes.conn.begin()