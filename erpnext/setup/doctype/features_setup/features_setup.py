class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl

	def validate(self):
		"""
			update settings in defaults
		"""
		from webnotes.model import default_fields 
		from webnotes.utils import set_default
		for key in self.doc.fields:
			if key not in default_fields:
				set_default(key, self.doc.fields[key])
