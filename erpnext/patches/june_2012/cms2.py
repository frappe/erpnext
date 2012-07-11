def execute():
	import webnotes
	import webnotes.model.sync
	
	# sync web page, blog doctype
	webnotes.model.sync.sync('website', 'web_page')
	webnotes.model.sync.sync('website', 'blog')

	cleanup()

	save_pages()
	
def cleanup():
	import webnotes
		
	# delete pages from `tabPage` of module Website or of type Webpage
	webnotes.conn.sql("""\
		delete from `tabPage`
		where module='Website' and ifnull(web_page, 'No') = 'Yes'""")
	
	# change show_in_website value in item table to 0 or 1
	webnotes.conn.sql("""\
		update `tabItem`
		set show_in_website = if(show_in_website = 'Yes', 1, 0)
		where show_in_website is not null""")
		
	# move comments from comment_doctype Page to Blog
	webnotes.conn.sql("""\
		update `tabComment` comm, `tabBlog` blog
		set comm.comment_doctype = 'Blog', comm.comment_docname = blog.name
		where comm.comment_docname = blog.page_name""")
	
	
def save_pages():
	"""save all web pages, blogs to create content"""
	import website.web_cache
	website.web_cache.rebuild_web_cache()