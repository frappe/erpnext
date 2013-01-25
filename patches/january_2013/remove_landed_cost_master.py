def execute():
	import webnotes
	webnotes.delete_doc("DocType", "Landed Cost Master")
	webnotes.delete_doc("DocType", "Landed Cost Master Detail")