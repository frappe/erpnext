# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import get_fullname
from frappe.model.document import Document
from erpnext.hr.utils import set_employee_name
from erpnext.accounts.utils import validate_fiscal_year

class InvalidExpenseApproverError(frappe.ValidationError): pass

class ExpenseClaim(Document):
	def get_feed(self):
		return _("{0}: From {0} for {1}").format(self.approval_status,
			self.employee_name, self.total_claimed_amount)

	def validate(self):
		validate_fiscal_year(self.posting_date, self.fiscal_year, _("Posting Date"), self)
		self.validate_sanctioned_amount()
		self.validate_exp_details()
		self.validate_expense_approver()
		self.validate_task()
		set_employee_name(self)

	def on_submit(self):
		if self.approval_status=="Draft":
			frappe.throw(_("""Approval Status must be 'Approved' or 'Rejected'"""))
		if self.task:
			self.update_task()
			
	def on_cancel(self):
		if self.project:
			self.update_task()

	def validate_exp_details(self):
		if not self.get('expenses'):
			frappe.throw(_("Please add expense voucher details"))

	def validate_expense_approver(self):
		if self.exp_approver and "Expense Approver" not in frappe.get_roles(self.exp_approver):
			frappe.throw(_("{0} ({1}) must have role 'Expense Approver'")\
				.format(get_fullname(self.exp_approver), self.exp_approver), InvalidExpenseApproverError)
	
	def update_task(self):
		expense_amount = frappe.db.sql("""select sum(total_sanctioned_amount) from `tabExpense Claim` 
			where project = %s and task = %s and approval_status = "Approved" and docstatus=1""",(self.project, self.task))
			
		task = frappe.get_doc("Task", self.task)
		task.total_expense_claim = expense_amount
		task.save()

	def validate_task(self):
		if self.project and not self.task:
			frappe.throw(_("Task is Mandatory if Time Log is against a project"))

	def validate_sanctioned_amount(self):
		if self.total_sanctioned_amount > self.total_claimed_amount:
			frappe.throw(_("Total sanctioned amount cannot be greater than total claimed amount."))