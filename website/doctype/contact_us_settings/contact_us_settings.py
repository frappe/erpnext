# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import webnotes

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl

	def onload(self):
		"""load address"""
		if self.doc.query_options:
			self.query_options = filter(None, self.doc.query_options.replace(",", "\n").split())
		else:
			self.query_options = ["Sales", "Support", "General"]
		if self.doc.address:
			self.address = webnotes.bean("Address", self.doc.address).doc
			
	def on_update(self):
		from webnotes.webutils import clear_cache
		clear_cache("contact")