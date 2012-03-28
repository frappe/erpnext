def execute():
	import webnotes
	from webnotes.modules.module_manager import reload_doc

	reload_doc('stock', 'DocType Mapper', 'Sales Order-Delivery Note')
	reload_doc('accounts', 'DocType Mapper', 'Sales Order-Receivable Voucher')
	reload_doc('accounts', 'DocType Mapper', 'Delivery Note-Receivable Voucher')

	webnotes.conn.sql("delete from `tabField Mapper Detail` where parent = 'Sales Order-Delivery Note' and from_field = 'basic_rate' and to_field = 'basic_rate'")
