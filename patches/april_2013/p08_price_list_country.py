import webnotes

def execute():
	webnotes.reload_doc("Setup", "DocType", "Price List")
	webnotes.conn.sql("""update `tabPrice List` set valid_for_all_countries=1""")