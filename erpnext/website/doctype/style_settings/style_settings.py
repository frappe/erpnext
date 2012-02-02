class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
		
	def validate(self):
		"""make custom css"""
		from jinja2 import Template
		
		with open('erpnext/website/doctype/style_settings/custom_template.css', 'r') as f:
			temp = Template(f.read())
		
		self.doc.custom_css = temp.render(doc = self.doc)
		
		from webnotes.session_cache import clear_cache
		clear_cache('Guest')
		
		