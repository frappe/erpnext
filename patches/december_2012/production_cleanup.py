def execute():
	import webnotes
	from webnotes.model import delete_doc
	delete_doc("DocType", "Production Control")
	delete_doc("DocType", "BOM Control")