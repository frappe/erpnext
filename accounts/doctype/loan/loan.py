import webnotes
from webnotes.model.doc import make_autoname, Document

class DocType:
	def __init__(self, doc, doclist):
		self.doc, self.doclist = doc, doclist
		
	def autoname(self):
		"""
			Create Loan Id using naming_series pattern
		"""
		self.doc.name = make_autoname(self.doc.naming_series+ '.#####')
		
