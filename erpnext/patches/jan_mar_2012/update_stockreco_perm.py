from __future__ import unicode_literals
def execute():
	import webnotes
	webnotes.conn.sql("update `tabDocPerm` set cancel = 1 where parent = 'Stock Reconciliation' and ifnull(submit, 0) = 1")
