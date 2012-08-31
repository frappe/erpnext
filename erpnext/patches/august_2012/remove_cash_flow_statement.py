def execute():
	import webnotes
	webnotes.conn.sql("delete from `tabSearch Criteria` where name = 'cash_flow_statement'")