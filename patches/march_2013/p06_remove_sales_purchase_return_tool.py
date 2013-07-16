import webnotes

def execute():
	webnotes.delete_doc("DocType", "Sales and Purchase Return Item")
	webnotes.delete_doc("DocType", "Sales and Purchase Return Tool")