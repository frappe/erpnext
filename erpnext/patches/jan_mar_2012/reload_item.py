def execute():
	import webnotes
	from webnotes.modules.module_manager import reload_doc
	reload_doc('stock', 'doctype', 'item')

	webnotes.conn.sql("update `tabItem` set re_order_qty = min_order_qty")
