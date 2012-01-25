"""
generate home html
"""

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
		
	def on_update(self):
		"""make home html"""
		import os, jinja2, markdown2
		import webnotes
		
		# markdown
		self.doc.main_section_html = markdown2.markdown(self.doc.main_section or '', \
			extras=["wiki-tables"])
		self.doc.side_section_html = markdown2.markdown(self.doc.side_section or '', \
			extras=["wiki-tables"])
		
		# write template
		with open(os.path.join(os.path.dirname(__file__), 'template.html'), 'r') as f:
			temp = jinja2.Template(f.read())
		
		html = temp.render(doc = self.doc.fields)
		webnotes.conn.set_value('Page', 'Home', 'content', html)
		