from __future__ import unicode_literals
def execute():
	import webnotes
	from webnotes.modules import reload_doc
	reload_doc('selling', 'search_criteria', 'itemwise_sales_details')
	reload_doc('selling', 'search_criteria', 'itemwise_delivery_details')

