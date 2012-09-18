from __future__ import unicode_literals
def execute():
	import webnotes
	webnotes.conn.sql("update `tabDocField` set options = replace(options, 'Others', 'Other') where fieldname = 'purpose' and parent = 'Stock Entry'")
