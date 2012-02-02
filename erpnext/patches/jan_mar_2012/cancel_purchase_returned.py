def execute():
	"""
		Set docstatus = 2 where status = 'Purchase Returned' for serial no
	"""
	import webnotes
	webnotes.conn.sql("""\
		UPDATE `tabSerial No` SET docstatus=2
		WHERE status='Purchase Returned'""")
