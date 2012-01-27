"""
generate html
"""
import webnotes

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
		
	def on_update(self):
		"""make home html"""
		from website.utils import make_template
		import os
		path = os.path.join(os.path.dirname(__file__), 'template.html')
		
		webnotes.conn.set_value('Page', 'contact', 'content', make_template(self.doc, path))
