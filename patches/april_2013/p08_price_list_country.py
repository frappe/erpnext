import webnotes

def execute():
	webnotes.conn.sql("""update `tabPrice List` set valid_for_all_countries=1""")