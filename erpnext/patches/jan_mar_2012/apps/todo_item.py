def execute():
	"""
		* Reload ToDo Item
	"""
	from webnotes.modules.module_manager import reload_doc
	reload_doc('utilities', 'doctype', 'todo_item')
