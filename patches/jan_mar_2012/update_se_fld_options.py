from __future__ import unicode_literals
def execute():
	import webnotes
	webnotes.conn.sql("update `tabDocField` set options = 'BOM' where fieldname = 'bom_no' and parent = 'Stock Entry'")

	from webnotes.modules import reload_doc
	reload_doc('stock', 'doctype', 'stock_entry')
