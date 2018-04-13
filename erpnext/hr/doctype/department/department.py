# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils.nestedset import NestedSet
from erpnext.utilities.transaction_base import delete_events
from frappe.model.document import Document

class Department(NestedSet):
	def validate(self):
		self.validate_employee_leave_approver()
		self.validate_employee_expense_approver()

	def validate_employee_leave_approver(self):
		for l in self.get("leave_approvers")[:]:
			if "Leave Approver" not in frappe.get_roles(l.leave_approver):
				frappe.get_doc("User", l.leave_approver).add_roles("Leave Approver")

	def validate_employee_expense_approver(self):
		for e in self.get("expense_approvers")[:]:
			if "Expense Approver" not in frappe.get_roles(e.expense_approver):
				frappe.get_doc("User", e.expense_approver).add_roles("Expense Approver")

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