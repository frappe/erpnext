def execute():
	import webnotes
	from webnotes.modules.module_manager import reload_doc
	reload_doc('setup', 'doctype', 'manage_account')
	reload_doc('stock', 'doctype', 'item')
	webnotes.conn.sql("alter table `tabItem` drop column `minimum_inventory_level`")
	webnotes.conn.sql("update `tabItem` set re_order_level = minimum_inventory_level wehre ifnull(re_order_level,0) = 0 ")
		