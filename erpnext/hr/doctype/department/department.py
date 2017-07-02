# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.model.document import Document
import frappe.utils.nestedset

class Department(Document):
	nsm_parent_field = 'parent_department'

	def validate(self):
		pass


	def on_update(self):
		self.update_nsm_model()

	def on_trash(self):
		self.validate_trash()
		self.update_nsm_model()

	def update_nsm_model(self):
		"""update lft, rgt indices for nested set model"""
		frappe.utils.nestedset.update_nsm(self)


	def validate_trash(self):
		pass


