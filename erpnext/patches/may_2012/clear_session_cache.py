def execute():
	import webnotes
	webnotes.conn.sql("delete from __SessionCache")