from __future__ import unicode_literals
def execute():
	import webnotes
	webnotes.conn.sql("update `tabDocField` set `default` = '' where fieldname = 'cost_center' and parent = 'RV Detail' and `default` = 'Purchase - TC'")
