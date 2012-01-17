import webnotes
def execute():
	"""
		Patch includes:
		* Reload of Stock Entry Detail
	"""
	from webnotes.modules.module_manager import reload_doc

	reload_doc('stock', 'doctype', 'stock_entry_detail')
	reload_doc('stock', 'doctype', 'item_supplier')
	reload_doc('stock', 'doctype', 'item')
