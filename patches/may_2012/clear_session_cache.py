from __future__ import unicode_literals
def execute():
	import webnotes
	webnotes.conn.sql("delete from __SessionCache")