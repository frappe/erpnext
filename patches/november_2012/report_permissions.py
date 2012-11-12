import webnotes

def execute():
	webnotes.conn.sql("""update tabDocPerm set `write`=1 where
		parent='Report'
		and role in ('Administrator', 'Report Manager', 'System Manager')""")