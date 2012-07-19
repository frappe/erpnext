from __future__ import unicode_literals
def execute():
	import webnotes
	from webnotes.model import delete_doc
	delete_doc("Search Criteria", "sales_order_pending_items1")
	
	webnotes.conn.sql("update `tabSearch Criteria` set module = 'Selling' where module = 'CRM'")
	from webnotes.modules import reload_doc
	reload_doc('selling', 'search_criteria', 'sales_order_pending_items')