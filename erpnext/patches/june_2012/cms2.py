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
	
def save_pages():
	"""save all web pages, blogs to create content"""
	import webnotes
	from webnotes.model.doclist import DocList
	save_list = [
		{
			'doctype': 'Web Page',
			'query': """select name from `tabWeb Page` where docstatus=0"""
		},
		{
			'doctype': 'Blog',
			'query': """\
				select name from `tabBlog`
				where docstatus = 0 and ifnull(published, 0) = 1"""
		},
		{
			'doctype': 'Item',
			'query': """\
				select name from `tabItem`
				where docstatus = 0 and ifnull(show_in_website, 'No') = 'Yes'"""
		}
	]
	
	for s in save_list:
		for p in webnotes.conn.sql(s['query'], as_dict=1):
			DocList(s['doctype'], p['name']).save()