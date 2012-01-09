def execute():
	import webnotes
	from webnotes.modules.module_manager import reload_doc
	
	reload_doc('stock', 'doctype', 'stock_reconciliation')
	webnotes.conn.sql("delete from `tabDocField` where (label in ('Validate Data', 'Attachment HTML', 'Attachment') or fieldname in ('next_step', 'company', 'fiscal_year', 'amendment_date')) and parent = 'Stock Reconciliation'")
