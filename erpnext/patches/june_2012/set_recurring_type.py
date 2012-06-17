def execute():
	import webnotes
	from webnotes.modules import reload_doc
	reload_doc('accounts', 'doctype', 'sales_invoice')
	
	webnotes.conn.sql("update `tabSales Invoice` set recurring_type = 'Monthly' where ifnull(convert_into_recurring_invoice, 0) = 1")