import webnotes

def execute():
	webnotes.clear_perms("Leave Application")
	webnotes.reload_doc("hr", "doctype", "leave_application")

	webnotes.clear_perms("Expense Claim")
	webnotes.reload_doc("hr", "doctype", "expense_claim")
	
	webnotes.conn.sql("""update `tabExpense Claim` set approval_status='Approved'
		where approval_status='Approved '""")

	webnotes.conn.commit()
	for t in ['__CacheItem', '__SessionCache', 'tabSupport Ticket Response']:
		webnotes.conn.sql("drop table if exists `%s`" % t)