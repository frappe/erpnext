def execute():
	import webnotes
	gd = webnotes.model.code.get_obj('Global Defaults')
	gd.doc.maintain_same_rate = 1
	gd.doc.save()
	gd.on_update()
	