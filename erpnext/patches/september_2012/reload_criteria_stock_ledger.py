def execute():
	import webnotes
	from webnotes.modules import reload_doc
	reload_doc('stock', 'Search Criteria', 'Stock Ledger')

	from webnotes.model import delete_doc
	delete_doc("Report", "Stock Ledger")