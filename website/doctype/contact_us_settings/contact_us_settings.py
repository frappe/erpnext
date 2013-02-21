# For license information, please see license.txt

from __future__ import unicode_literals
import webnotes

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl

	def onload(self):
		"""load address"""
		if self.doc.query_options:
			self.doc.query_options = filter(None, self.doc.query_options.replace(",", "\n").split())
		else:
			self.doc.query_options = ["Sales", "Support", "General"]
		if self.doc.address:
			self.address = webnotes.bean("Address", self.doc.address).doc
			
	def on_update(self):
		from website.utils import clear_cache
		clear_cache("contact")