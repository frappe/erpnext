from __future__ import unicode_literals
def execute():
	import webnotes
	from webnotes.modules import reload_doc
	reload_doc('stock', 'doctype', 'stock_entry')

	webnotes.conn.sql("update `tabDocField` set options = concat(options, '\nOthers') where fieldname = 'purpose' and parent = 'Stock Entry'")
