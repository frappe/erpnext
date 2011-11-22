def execute():
	import webnotes
	from webnotes.modules.module_manager import reload_doc

	reload_doc('accounts', 'doctype', 'payable_voucher')
	reload_doc('buying', 'doctype', 'purchase_common')
	reload_doc('stock', 'doctype', 'purchase_receipt_detail')
