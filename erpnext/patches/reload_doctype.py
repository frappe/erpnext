def execute():
	import webnotes
	from webnotes.modules.module_manager import reload_doc
	reload_doc('core', 'doctype', 'doctype')
