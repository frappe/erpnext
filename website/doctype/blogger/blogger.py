# For license information, please see license.txt

from __future__ import unicode_literals
import webnotes

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
		
	def on_update(self):
		"if profile is set, then update all older blogs"
		if self.doc.profile:
			for blog in webnotes.conn.sql_list("""select name from tabBlog where owner=%s 
				and ifnull(blogger,'')=''""", self.doc.profile):
				b = webnotes.bean("Blog", blog)
				b.doc.blogger = self.doc.name
				b.save()
				
