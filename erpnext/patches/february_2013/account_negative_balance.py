# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

def execute():
	import webnotes
	webnotes.reload_doc("accounts", "doctype", "account")
	webnotes.conn.sql("update `tabAccount` set allow_negative_balance = 1")