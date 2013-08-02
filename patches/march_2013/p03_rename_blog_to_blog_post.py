# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

import webnotes

def execute():
	webnotes.reload_doc('website', 'doctype', 'blogger')
	webnotes.rename_doc("DocType", "Blog", "Blog Post", force=True)
	webnotes.reload_doc('website', 'doctype', 'blog_post')
	webnotes.conn.sql('''update tabBlogger set posts=(select count(*) 
		from `tabBlog Post` where ifnull(blogger,"")=tabBlogger.name)''')
	webnotes.conn.sql("""update `tabBlog Post` set published_on=date(creation)""")
