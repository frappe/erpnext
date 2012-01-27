"""
record of files

naming for same name files: file.gif, file-1.gif, file-2.gif etc
"""

import webnotes

class DocType():
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
		
	def autoname(self):
		"""save file by its name"""
		import re
		self.doc.name = re.sub('[~!@#$%^&*()<>,."\']', '', self.doc.title.lower())
		self.doc.name = '-'.join(self.doc.name.split()[:4])
		if webnotes.conn.sql("""select name from tabBlog where name=%s""", self.doc.name) or \
			webnotes.conn.sql("""select name from tabPage where name=%s""", self.doc.name):
			webnotes.msgprint("Another page with similar title exists, please change the title",\
				raise_exception=1)
	
	def on_update(self):
		"""write/update 'Page' with the blog"""
		from webnotes.model.doc import Document
		
		if webnotes.conn.sql("""select name from tabPage where name=%s""", self.doc.name):
			p = Document('Page', self.doc.name)
		else:
			p = Document('Page')
			
		p.title = self.doc.title
		p.name = p.page_name = self.doc.name
		p.module = 'Website'
		p.standard = 'No'
		
		from jinja2 import Template
		import markdown2
		import os
		
		self.doc.content_html = markdown2.markdown(self.doc.content or '')
		
		with open(os.path.join(os.path.dirname(__file__), 'template.html'), 'r') as f:
			p.content = Template(f.read()).render(doc=self.doc)
		
		with open(os.path.join(os.path.dirname(__file__), 'blog_page.js'), 'r') as f:
			p.script = Template(f.read()).render(doc=self.doc)
		
		p.save()
		
		# add guest access
		if not webnotes.conn.sql("""select parent from `tabPage Role`
			where role='Guest' and parent=%s""", self.doc.name):
			d = Document('Page Role')
			d.parent = self.doc.name
			d.role = 'Guest'
			d.save()
			