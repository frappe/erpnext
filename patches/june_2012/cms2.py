# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
def execute():
	import webnotes
	
	# sync doctypes required for the patch
	webnotes.reload_doc('website', 'doctype', 'web_page')
	webnotes.reload_doc('website', 'doctype', 'website_settings')
	webnotes.reload_doc('stock', 'doctype', 'item')

	cleanup()

	save_pages()
	
	save_website_settings()
	
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
		
	# delete deprecated pages
	import webnotes.model
	for page in ['products', 'contact', 'blog', 'about']:
		try:
			webnotes.model.delete_doc('Page', page)
		except Exception, e:
			webnotes.modules.patch_handler.log(unicode(e))

	import os
	import conf
	# delete other html files
	exception_list = ['app.html', 'unsupported.html', 'blank.html']
	conf_dir = os.path.dirname(os.path.abspath(conf.__file__))
	public_path = os.path.join(conf_dir, 'public')
	for f in os.listdir(public_path):
		if f.endswith('.html') and f not in exception_list:
			os.remove(os.path.join(public_path, f))

def save_pages():
	"""save all web pages, blogs to create content"""
	query_map = {
		'Web Page': """select name from `tabWeb Page` where docstatus=0""",
		'Blog': """\
			select name from `tabBlog`
			where docstatus = 0 and ifnull(published, 0) = 1""",
		'Item': """\
			select name from `tabItem`
			where docstatus = 0 and ifnull(show_in_website, 0) = 1""",
	}

	import webnotes
	from webnotes.model.bean import Bean
	import webnotes.modules.patch_handler

	for dt in query_map:
		for result in webnotes.conn.sql(query_map[dt], as_dict=1):
			try:
				Bean(dt, result['name'].encode('utf-8')).save()
			except Exception, e:
				webnotes.modules.patch_handler.log(unicode(e))
			
def save_website_settings():
	from webnotes.model.code import get_obj
	
	# rewrite pages
	get_obj('Website Settings').on_update()
	
	ss = get_obj('Style Settings')
	ss.validate()
	ss.doc.save()
	ss.on_update()