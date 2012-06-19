def execute():
	import webnotes
	from webnotes.model.doclist import DocList
	import webnotes.model.sync
	
	# sync web page doctype
	webnotes.model.sync.sync('website', 'web_page')
	
	# save all web pages to create content
	for p in webnotes.conn.sql("""select name from `tabWeb Page` where docstatus=0"""):
		DocList('Web Page', p[0]).save()