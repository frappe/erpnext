import webnotes

def execute():
	from webnotes.model.doclist import DocList
	import os
		
	for name in webnotes.conn.sql("""select name from `tabWeb Page` where docstatus=0"""):
		print name
		DocList('Web Page', name[0]).save()