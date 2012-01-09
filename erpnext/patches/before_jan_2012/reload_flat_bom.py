def execute():
	from webnotes.modules import webnotes
	from webnotes.modules.module_manager import reload_doc

	reload_doc('production', 'doctype', 'flat_bom_detail')
	reload_doc('production', 'doctype', 'bom_material')
