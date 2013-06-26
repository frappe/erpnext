# For license information, please see license.txt

from __future__ import unicode_literals
import webnotes

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
		
	def validate(self):
		for key in ["supplier_type", "maintain_same_rate"]:
			webnotes.conn.set_default(key, self.doc.fields.get(key, ""))
	