from __future__ import unicode_literals
def execute():
	import webnotes
	count = webnotes.conn.sql("""SELECT COUNT(*) FROM `tabTable Mapper Detail`
		WHERE parent='Sales Order-Sales Invoice'
		AND from_table='Sales Order Item'""")
	if count and count[0][0]==2:
		webnotes.conn.sql("""DELETE FROM `tabTable Mapper Detail`
			WHERE parent='Sales Order-Sales Invoice'
			AND from_table='Sales Order Item'
			AND validation_logic='docstatus = 1'""")
