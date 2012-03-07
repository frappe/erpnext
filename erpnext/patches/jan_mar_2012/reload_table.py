def execute():
	import webnotes
	from webnotes.modules.module_manager import reload_doc
	reload_doc('selling', 'doctype', 'quotation_detail')
	reload_doc('selling', 'doctype', 'sales_order_detail')
	reload_doc('stock', 'doctype', 'delivery_note_detail')
	reload_doc('stock', 'doctype', 'purchase_receipt_detail')
	reload_doc('buying', 'doctype', 'po_detail')
	reload_doc('accounts', 'doctype', 'rv_detail')
	reload_doc('accounts', 'doctype', 'pv_detail')

