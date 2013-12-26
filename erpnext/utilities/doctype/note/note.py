# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import webnotes

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
		
	def autoname(self):
		# replace forbidden characters
		import re
		self.doc.name = re.sub("[%'\"#*?`]", "", self.doc.title.strip())
		
	def onload(self):
		if not self.doc.public and webnotes.session.user != self.doc.owner:
			if webnotes.session.user not in [d.user for d in self.doclist if d.doctype=="Note User"]:
				webnotes.msgprint("You are not authorized to read this record.", raise_exception=True)
	
	def validate(self):
		if not self.doc.fields.get("__islocal"):
			if webnotes.session.user != self.doc.owner:
				if webnotes.session.user not in webnotes.conn.sql_list("""select user from `tabNote User` 
					where parent=%s and permission='Edit'""", self.doc.name):
					webnotes.msgprint("You are not authorized to edit this record.", raise_exception=True)
