from __future__ import unicode_literals
def execute():
	import webnotes
	from webnotes.modules import reload_doc
	reload_doc('buying', 'DocType Mapper', 'Material Request-Purchase Order')