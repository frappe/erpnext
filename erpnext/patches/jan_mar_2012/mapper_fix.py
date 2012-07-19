from __future__ import unicode_literals
def execute():
	import webnotes
	webnotes.conn.sql("delete from `tabTable Mapper Detail` where to_table = 'Sales Invoice Item' and parent = 'Delivery Note-Sales Invoice' and validation_logic = 'amount > ifnull(billed_amt, 0) and docstatus = 1'")
