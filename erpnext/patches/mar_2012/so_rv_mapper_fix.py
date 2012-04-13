def execute():
	import webnotes
	count = webnotes.conn.sql("""SELECT COUNT(*) FROM `tabTable Mapper Detail`
		WHERE parent='Sales Order-Receivable Voucher'
		AND from_table='Sales Order Detail'""")
	if count and count[0][0]==2:
		webnotes.conn.sql("""DELETE FROM `tabTable Mapper Detail`
			WHERE parent='Sales Order-Receivable Voucher'
			AND from_table='Sales Order Detail'
			AND validation_logic='docstatus = 1'""")
