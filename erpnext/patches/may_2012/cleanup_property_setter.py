def execute():
	import webnotes
	webnotes.conn.sql("delete from `tabProperty Setter` where property in ('width', 'previous_field')")
