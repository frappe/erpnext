def execute():
	import webnotes
	webnotes.conn.sql("update `tabDocField` set `default`='' where parent = 'Receivable Voucher' and fieldname = 'naming_series' and `default` = 'INV'")
