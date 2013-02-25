import webnotes

def execute():
	webnotes.clear_perms("Report")
	webnotes.clear_perms("ToDo")
	webnotes.reload_doc("core", "doctype", "report")
	webnotes.reload_doc("core", "doctype", "todo")
	webnotes.reload_doc("core", "report", "todo")
