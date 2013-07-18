def execute():
	import webnotes
	webnotes.reload_doc("setup", "doctype", "global_defaults")
	
	gd = webnotes.bean('Global Defaults')
	gd.doc.maintain_same_sales_rate = 1
	gd.save()