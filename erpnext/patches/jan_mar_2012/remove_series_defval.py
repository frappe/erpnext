from __future__ import unicode_literals
def execute():
	import webnotes
	webnotes.conn.sql("update `tabDocField` set `default`='' where parent = 'Sales Invoice' and fieldname = 'naming_series' and `default` = 'INV'")
