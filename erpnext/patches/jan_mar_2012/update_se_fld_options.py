def execute():
	import webnotes
	webnotes.conn.sql("update `tabDocField` set options = 'BOM' where fieldname = 'bom_no' and parent = 'Stock Entry'")

	from webnotes.modules.module_manager import reload_doc
	reload_doc('stock', 'doctype', 'stock_entry')
