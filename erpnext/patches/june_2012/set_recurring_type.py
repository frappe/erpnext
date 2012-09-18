from __future__ import unicode_literals
def execute():
	import webnotes
	from webnotes.model.sync import sync
	sync('accounts', 'sales_invoice')
	
	webnotes.conn.sql("update `tabSales Invoice` set recurring_type = 'Monthly' where ifnull(convert_into_recurring_invoice, 0) = 1")