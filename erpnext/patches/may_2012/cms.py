import webnotes

def execute():
	from webnotes.model.code import get_obj
	
	# rewrite pages
	get_obj('Website Settings').on_update()
	
	ss = get_obj('Style Settings')
	ss.validate()
	ss.doc.save()
	ss.on_update()