def execute():
	import webnotes
	from webnotes.model import delete_doc
	delete_doc("Search Criteria", "sales_order_pending_items1")
	
	from webnotes.modules import reload_doc
	reload_doc('selling', 'search_criteria', 'sales_order_pending_items')