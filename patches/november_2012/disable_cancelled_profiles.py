import webnotes
def execute():
	"""
		in old system, deleted profiles were set as docstatus=2
		in new system, its either disabled or deleted.
	"""
	webnotes.conn.sql("""update `tabProfile` set docstatus=0, enabled=0
		where docstatus=2""")