from __future__ import unicode_literals
def execute():
	import webnotes
	webnotes.conn.sql("""\
		update `tabDocPerm` set `match`=NULL
		where parent='Event' and role='All' and permlevel=0""")