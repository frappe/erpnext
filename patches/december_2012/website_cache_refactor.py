# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import webnotes

def execute():
	# set page published = 1
	webnotes.reload_doc("website", "doctype", "web_page")
	webnotes.conn.sql("""update `tabWeb Page` set published=1;""")

	# convert all page & blog markdowns to html
	from markdown2 import markdown

	for page in webnotes.conn.sql("""select name, main_section from `tabWeb Page`"""):
		m = markdown(page[1] or "").encode("utf8")
		webnotes.conn.set_value("Web Page", page[0], "main_section", m)

	for page in webnotes.conn.sql("""select name, content from `tabBlog`"""):
		m = markdown(page[1] or "").encode("utf8")
		webnotes.conn.set_value("Blog", page[0], "content", m)

	# delete website cache
	webnotes.delete_doc("DocType", "Web Cache")
	webnotes.conn.commit()
	webnotes.conn.sql("""drop table if exists `tabWeb Cache`""")