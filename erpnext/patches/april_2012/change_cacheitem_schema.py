def execute():
	import webnotes
	webnotes.conn.sql("alter table __CacheItem modify `value` longtext")
