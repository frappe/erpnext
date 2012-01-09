def execute():
	import webnotes
	webnotes.conn.sql("update `tabDocField` set print_hide = 1 where fieldname in ('price_list_currency', 'plc_conversion_rate')")
