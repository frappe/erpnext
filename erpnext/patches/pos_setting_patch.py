def execute():
	import webnotes
	webnotes.conn.sql("update `tabDocField` set `default` = 1 where fieldname = 'conversion_rate' and parent = 'POS Setting'")

	from webnotes.model import delete_doc
	delete_doc('DocType', 'POS Settings')
