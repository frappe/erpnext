import webnotes
def execute():
	webnotes.reload_doc("website", "doctype", "web_page")
	webnotes.reload_doc("website", "doctype", "blog")
	webnotes.reload_doc("stock", "doctype", "item")
	webnotes.reload_doc("setup", "doctype", "item_group")
	
	# build wn-web.js and wn-web.css
	from website.helpers.make_web_include_files import make
	make()

	import website.utils
	website.utils.clear_cache()