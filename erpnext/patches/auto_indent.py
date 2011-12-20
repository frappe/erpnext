def execute():
	import webnotes
	from webnotes.modules.module_manager import reload_doc
	reload_doc('manage_account', 'doctype', 'auto_indent')
	reload_doc('item', 'doctype', 'email_notify')
	webnotes.conn.sql("update `tabItem` set re_order_level = min_order_qty where re_order_level=''")
		
