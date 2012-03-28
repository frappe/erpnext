def execute():
	import webnotes
	webnotes.conn.sql("""DELETE FROM `tabTable Mapper Detail`
		WHERE parent='Sales Order-Receivable Voucher'
		AND from_table='Sales Order Detail'""")
	from webnotes.modules.module_manager import reload_doc
	reload_doc('accounts', 'DocType Mapper', 'Sales Order-Receivable Voucher')
