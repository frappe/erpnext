# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

from frappe.model.document import Document

class Note(Document):
		
	def autoname(self):
		# replace forbidden characters
		import re
		self.name = re.sub("[%'\"#*?`]", "", self.title.strip())
		
	def onload(self):
		if not self.public and frappe.session.user != self.owner:
			if frappe.session.user not in [d.user for d in self.get("share_with")]:
				frappe.msgprint("You are not authorized to read this record.", raise_exception=True)
	
	def validate(self):
		if not self.get("__islocal"):
			if frappe.session.user != self.owner:
				if frappe.session.user not in frappe.db.sql_list("""select user from `tabNote User` 
					where parent=%s and permission='Edit'""", self.name):
					frappe.msgprint("You are not authorized to edit this record.", raise_exception=True)
