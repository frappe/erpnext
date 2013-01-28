def execute():
	import webnotes
	webnotes.conn.commit()
	webnotes.conn.sql("""alter table tabSessions engine=MyISAM""")