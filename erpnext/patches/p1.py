def execute():
	import webnotes
	if not webnotes.conn.sql("select name from tabDocFormat where parent = 'Receivable Voucher' and format != 'POS Invoice'"):
		webnotes.conn.sql("update tabDocType set default_print_format = 'Standard' where name =  'Receivable Voucher'")
