def execute():
	import webnotes
	from webnotes.modules.module_manager import reload_doc
	from webnotes.model import delete_doc

	delete_doc('DocType', 'Landed Cost Wizard')
	reload_doc('stock', 'doctype', 'landed_cost_wizard')
	reload_doc('stock', 'doctype', 'lc_pr_detail')
