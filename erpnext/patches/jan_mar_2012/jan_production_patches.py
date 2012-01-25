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

	webnotes.conn.sql("""
		UPDATE tabDocField SET fieldtype='Float'
		WHERE parent='Bill Of Materials'
		AND fieldname IN ('operating_cost', 'raw_material_cost', 'total_cost')
	""")

	webnotes.conn.sql("""
		UPDATE tabDocField SET fieldtype='Float'
		WHERE parent='BOM Material'
		AND fieldname IN ('qty', 'rate', 'amount', 'qty_consumed_per_unit')
	""")
	
	reload_doc('stock', 'doctype', 'stock_entry')
	reload_doc('production', 'doctype', 'bill_of_materials')
	reload_doc('production', 'doctype', 'bom_material')
