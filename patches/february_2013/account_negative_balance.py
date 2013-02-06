def execute():
	import webnotes
	webnotes.reload_doc("accounts", "doctype", "account")
	webnotes.conn.sql("update `tabAccount` set allow_negative_balance = 1")