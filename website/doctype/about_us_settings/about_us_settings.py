# For license information, please see license.txt

from __future__ import unicode_literals
import webnotes
from website.utils import url_for_website

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
			
	def on_update(self):
		from website.utils import clear_cache
		clear_cache("about")
		
def get_args():
	obj = webnotes.get_obj("About Us Settings")
	for d in obj.doclist.get({"doctype":"About Us Team Member"}):
		if not "/" in d.image_link:
			d.image_link = "files/" + d.image_link
	return {
		"obj": obj
	}