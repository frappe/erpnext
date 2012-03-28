def execute():
	import webnotes
	webnotes.conn.sql("delete from `tabTable Mapper Detail` where to_table = 'RV Detail' and parent = 'Delivery Note-Receivable Voucher' and validation_logic = 'amount > ifnull(billed_amt, 0) and docstatus = 1'")
