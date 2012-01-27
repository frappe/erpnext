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
		
		self.doc.about_team = webnotes.conn.sql("""select * from `tabAbout Us Team` 
			where parent='About Us Settings'""", as_dict=1)
		
		import markdown2
		for t in self.doc.about_team:
			t['bio'] = markdown2.markdown(t['bio'])
		
		webnotes.conn.set_value('Page', 'about', 'content', make_template(self.doc, path))
