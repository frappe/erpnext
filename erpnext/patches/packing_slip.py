def execute():
	import webnotes
	from webnotes.modules.module_manager import reload_doc
	reload_doc('stock', 'doctype', 'delivery_note_detail')
	reload_doc('stock', 'Print Format', 'Delivery Note Packing List Wise')
	
	webnotes.conn.sql("delete from `tabDocField` where fieldname in ('packed_by', 'packing_checked_by', 'pack_size') and parent = 'Delivery Note'")
	
