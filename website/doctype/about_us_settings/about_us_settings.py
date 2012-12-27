# For license information, please see license.txt

from __future__ import unicode_literals
import webnotes
from website.utils import url_for_website

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
		
	def onload(self):
		"""load employee"""
		emp_list = []
		for d in self.doclist.get({"doctype":"About Us Team Member"}):
			emp = webnotes.doc("Employee", d.employee)
			emp.image = url_for_website(emp.image)
			emp_list.append(emp)
		self.doclist += emp_list
	
	def on_update(self):
		from website.utils import clear_cache
		clear_cache("about")