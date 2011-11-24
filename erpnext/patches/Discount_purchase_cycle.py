def execute():
	import webnotes
	from webnotes.modules.module_manager import reload_doc

	reload_doc('accounts', 'doctype', 'pv_detail')
	reload_doc('buying', 'doctype', 'po_detail')
	reload_doc('stock', 'doctype', 'purchase_receipt_detail')
