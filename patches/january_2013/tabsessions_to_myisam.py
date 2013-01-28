def execute():
	import webnotes
	webnotes.conn.sql("""alter table tabSessions engine=MyISAM""")