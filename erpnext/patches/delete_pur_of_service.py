def execute():
	import webnotes
	from webnotes.model import delete_doc
	delete_doc('DocType', 'Purpose of Service')
