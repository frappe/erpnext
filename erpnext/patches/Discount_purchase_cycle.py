def execute():
	import webnotes
	from webnotes.modules.module_manager import reload_doc

	reload_doc('accounts', 'doctype', 'pv_detail')
	reload_doc('buying', 'doctype', 'po_detail')
	reload_doc('stock', 'doctype', 'purchase_receipt_detail')
	if webnotes.conn.sql("select name from `tabDocField` where parent = 'PO Detail' and fieldname = 'discount'"):
		webnotes.conn.sql("update `tabPO Detail` set discount_rate=discount")
