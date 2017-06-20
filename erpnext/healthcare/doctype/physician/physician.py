# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS LLP and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import throw, _
from frappe.utils import cstr
from erpnext.accounts.party import validate_party_accounts
from frappe.contacts.address_and_contact import load_address_and_contact, delete_contact_and_address

class Physician(Document):
	def onload(self):
		load_address_and_contact(self)

	def autoname(self):
		# physician first_name and last_name
		self.name = " ".join(filter(None,
			[cstr(self.get(f)).strip() for f in ["first_name","middle_name","last_name"]]))

	def validate(self):
		validate_party_accounts(self)
		if self.user_id:
			self.validate_for_enabled_user_id()
			self.validate_duplicate_user_id()
			existing_user_id = frappe.db.get_value("Physician", self.name, "user_id")
			if(self.user_id != existing_user_id):
				frappe.permissions.remove_user_permission(
					"Physician", self.name, existing_user_id)


		else:
			existing_user_id = frappe.db.get_value("Physician", self.name, "user_id")
			if existing_user_id:
				frappe.permissions.remove_user_permission(
					"Physician", self.name, existing_user_id)

	def on_update(self):
		if self.user_id:
			frappe.permissions.add_user_permission("Physician", self.name, self.user_id)


	def validate_for_enabled_user_id(self):
		enabled = frappe.db.get_value("User", self.user_id, "enabled")
		if enabled is None:
			frappe.throw(_("User {0} does not exist").format(self.user_id))
		if enabled == 0:
			frappe.throw(_("User {0} is disabled").format(self.user_id))

	def validate_duplicate_user_id(self):
		physician = frappe.db.sql_list("""select name from `tabPhysician` where
			user_id=%s and name!=%s""", (self.user_id, self.name))
		if physician:
			throw(_("User {0} is already assigned to Physician {1}").format(
				self.user_id, physician[0]), frappe.DuplicateEntryError)

	def on_trash(self):
		delete_contact_and_address('Physician', self.name)
