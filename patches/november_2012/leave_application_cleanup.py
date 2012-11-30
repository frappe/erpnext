import webnotes

def execute():
	webnotes.clear_perms("Leave Application")
	webnotes.reload_doc("hr", "doctype", "leave_application")
	webnotes.conn.sql("""update `tabLeave Application` set status='Approved'
		where docstatus=1""")
	webnotes.conn.sql("""update `tabLeave Application` set status='Open'
		where docstatus=0""")		