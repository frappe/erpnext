import webnotes

def execute():
	from webnotes.model.code import get_obj
	
	# rewrite pages
	get_obj('Website Settings').rewrite_pages()