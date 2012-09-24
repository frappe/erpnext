from __future__ import unicode_literals
def execute():
	import webnotes
	from webnotes.modules import reload_doc
	reload_doc('stock', 'doctype', 'serial_no')

	webnotes.conn.sql("update `tabSerial No` set sle_exists = 1")
