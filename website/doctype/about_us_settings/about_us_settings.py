# For license information, please see license.txt

from __future__ import unicode_literals
import webnotes

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
			
	def on_update(self):
		from webnotes.webutils import clear_cache
		clear_cache("about")
		
def get_args():
	obj = webnotes.get_obj("About Us Settings")
	return {
		"obj": obj
	}