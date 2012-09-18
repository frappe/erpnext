from __future__ import unicode_literals
def execute():
	import webnotes
	import webnotes.modules
	webnotes.modules.reload_doc('selling', 'search_criteria', 'customer_address_contact')