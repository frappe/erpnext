def execute():
	import webnotes
	webnotes.conn.sql("DELETE FROM `tabDocFormat` WHERE format='POS Invoice'")
	from webnotes.modules.modules_manager import reload_doc
	reload_doc('accounts', 'Print Format', 'POS Invoice')
