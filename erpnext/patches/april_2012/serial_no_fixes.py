def execute():
	import webnotes
	from webnotes.modules.module_manager import reload_doc
	reload_doc('stock', 'doctype', 'serial_no')

	webnotes.conn.sql("update `tabSerial No` set sle_exists = 1")
