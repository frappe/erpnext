import webnotes

def execute():
	webnotes.clear_perms("Employee")
	webnotes.reload_doc("hr", "doctype", "employee")
	webnotes.conn.sql("""update tabEmployee set employee=name""")
