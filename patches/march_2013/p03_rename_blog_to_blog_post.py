import webnotes

def execute():
	webnotes.reload_doc('website', 'doctype', 'blogger')
	webnotes.conn.sql('''update tabBlogger set posts=(select count(*) 
		from tabBlog where ifnull(blogger,"")=tabBlogger.name)''')
	webnotes.rename_doc("DocType", "Blog", "Blog Post", force=True)
	webnotes.conn.sql("""update `tabBlog Post` set published_on=creation""")
