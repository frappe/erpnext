import webnotes
import website.utils

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
	
	def autoname(self):
		"""name from title"""
		self.doc.name = website.utils.page_name(self.doc.title)

	def validate(self):
		"""make page for this product"""					
		p = website.utils.add_page(self.doc.title)
		
		from jinja2 import Template
		import os
	
		website.utils.markdown(self.doc, ['main_section', 'side_section'])
		
		with open(os.path.join(os.path.dirname(__file__), 'template.html'), 'r') as f:
			p.content = Template(f.read()).render(doc=self.doc)

		p.save()
		
		website.utils.add_guest_access_to_page(p.name)
		
		del self.doc.fields['main_section_html']
		del self.doc.fields['side_section_html']
		