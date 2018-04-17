# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils.nestedset import NestedSet
from erpnext.utilities.transaction_base import delete_events
from frappe.model.document import Document

class Department(NestedSet):
	nsm_parent_field = 'parent_department'

	def update_nsm_model(self):
		frappe.utils.nestedset.update_nsm(self)

	def on_update(self):
		self.update_nsm_model()

	def on_trash(self):
		super(Department, self).on_trash()
		delete_events(self.doctype, self.name)

def on_doctype_update():
	frappe.db.add_index("Department", ["lft", "rgt"])