from __future__ import unicode_literals
def execute():
	import webnotes
	from webnotes.modules import reload_doc
	webnotes.conn.sql("delete from `tabField Mapper Detail` where from_field = 'transaction_date' and parent in ('Sales Order-Delivery Note', 'Purchase Order-Purchase Receipt')")

	reload_doc('stock', 'DocType Mapper', 'Sales Order-Delivery Note')
	reload_doc('stock', 'DocType Mapper', 'Purchase Order-Purchase Receipt')
