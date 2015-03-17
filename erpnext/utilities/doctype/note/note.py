# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class Note(Document):
	def autoname(self):
		# replace forbidden characters
		import re
		self.name = re.sub("[%'\"#*?`]", "", self.title.strip())

	def before_print(self):
		self.print_heading = self.name
		self.sub_heading = ""

def get_permission_query_conditions(user):
	if not user: user = frappe.session.user

	if user == "Administrator":
		return ""

	return """(`tabNote`.public=1 or `tabNote`.owner="{user}" or exists (
		select name from `tabNote User`
			where `tabNote User`.parent=`tabNote`.name
			and `tabNote User`.user="{user}"))""".format(user=frappe.db.escape(user))

def has_permission(doc, ptype, user):
	if doc.public == 1 or user == "Administrator":
		return True

	if user == doc.owner:
		return True

	note_user_map = dict((d.user, d) for d in doc.get("share_with"))
	if user in note_user_map:
		if ptype == "read":
			return True
		elif note_user_map.get(user).permission == "Edit":
			return True

	return False
