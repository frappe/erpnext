import webnotes
def execute():
	webnotes.reload_doc("stock", "doctype", "stock_ledger_entry")
	webnotes.reload_doc("stock", "doctype", "serial_no")
	webnotes.reload_doc("stock", "report", "stock_ledger")
	
	webnotes.conn.sql("""delete from `tabStock Ledger Entry` 
		where ifnull(is_cancelled, 'No') = 'Yes'""")
		
	webnotes.reload_doc("accounts", "doctype", "gl_entry")
	webnotes.conn.sql("""delete from `tabGL Entry` where ifnull(is_cancelled, 'No') = 'Yes'""")