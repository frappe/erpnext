# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS LLP and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class ServiceUnit(Document):
	def validate(self):
		for child in self.assigned_users:
			if child.user :
				validate_for_enabled_user(child.user)
				#validate_duplicate_user(child.user, self.name, child.name)

	def on_update(self):
		for child in self.assigned_users:
			if child.user :
				frappe.permissions.add_user_permission("Service Unit", self.name, child.user)

def validate_for_enabled_user(user):
	enabled = frappe.db.get_value("User", user, "enabled")
	if enabled is None:
		frappe.throw(_("User {0} does not exist").format(user))
	if enabled == 0:
		frappe.throw(_("User {0} is disabled").format(user))

def validate_duplicate_user(user, parent):
	users = frappe.db.sql_list("""select name from `tabUser List` where
		user=%s and parent=%s""", (user, parent))
	if users:
		frappe.throw(_("Service Unit {0} is already assigned to User {1}").format(parent, user), frappe.DuplicateEntryError)
