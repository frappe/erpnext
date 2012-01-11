def execute():
	import webnotes
	from webnotes.modules.module_manager import reload_doc
	reload_doc('Support', 'DocType', 'Support Ticket')
	from webnotes.model.code import get_obj
	get_obj('DocType', 'Support Ticket').validate()
