import webnotes
def execute():
	webnotes.reload_doc("setup", "doctype", "email_digest")
	webnotes.conn.sql('update `tabEmail Digest` set calendar_events=1, todo_list=1 where enabled=1')