"""
	Reload Task Doctype of Project Module
"""
def execute():
	from webnotes.modules.module_manager import reload_doc
	reload_doc('Projects', 'DocType', 'Ticket')

