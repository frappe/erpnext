def execute():
	import webnotes
	from webnotes.modules.module_manager import reload_doc

	reload_doc('accounts', 'doctype', 'receivable_voucher')
	reload_doc('stock', 'doctype', 'delivery_note')
	reload_doc('selling', 'doctype', 'sales_order')
	reload_doc('selling', 'doctype', 'quotation')
	reload_doc('setup', 'doctype', 'manage_account')


	for d in ['Receivable Voucher', 'Delivery Note', 'Sales Order', 'Quotation']:
		sql("update `tab%s` set price_list_currency = currency, plc_conversion_rate = conversion_rate" % d)
