import webnotes
def execute():
	webnotes.reload_doc("core", "doctype", "docperm")
	webnotes.reset_perms("Custom Script")
