from __future__ import unicode_literals
def execute():
	import webnotes
	sr = webnotes.conn.sql("select max(name) from `tabPage Role`")
	if sr and sr[0][0].startswith('PR'):
		webnotes.conn.sql("update tabSeries set current = %s where name = 'PR'", int(sr[0][0][2:]))	
