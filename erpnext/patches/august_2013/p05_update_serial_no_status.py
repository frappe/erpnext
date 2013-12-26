import webnotes

def execute():
	webnotes.conn.sql("""update `tabSerial No` set status = 'Not Available' where status='Not In Store'""")
	webnotes.conn.sql("""update `tabSerial No` set status = 'Available' where status='In Store'""")