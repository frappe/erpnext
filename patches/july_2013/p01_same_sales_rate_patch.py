def execute():
	import webnotes
	webnotes.reload_doc("setup", "doctype", "global_defaults")
	
	from webnotes.model.code import get_obj
	gd = get_obj('Global Defaults')
	gd.doc.maintain_same_sales_rate = 1
	gd.doc.save()
	gd.on_update()