import webnotes

def execute():
	webnotes.reload_doc("website", "doctype", "blog_post")
	from website.utils import clear_cache
	clear_cache()
