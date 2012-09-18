from __future__ import unicode_literals
def execute():
	import webnotes
	from webnotes.modules import reload_doc
	reload_doc('accounts', 'doctype', 'c_form')
