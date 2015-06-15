# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import get_fullname, flt
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
		self.validate_expense_approver()
		self.validate_task()
		self.calculate_total_amount()
		set_employee_name(self)

	def on_submit(self):
		if self.approval_status=="Draft":
			frappe.throw(_("""Approval Status must be 'Approved' or 'Rejected'"""))
		if self.task:
			self.update_task()
			
	def on_cancel(self):
		if self.task:
			self.update_task()
			
	def calculate_total_amount(self):
		self.total_claimed_amount = 0 
		self.total_sanctioned_amount = 0
		for d in self.get('expenses'):
			self.total_claimed_amount += flt(d.claim_amount)
			self.total_sanctioned_amount += flt(d.sanctioned_amount)

	def validate_expense_approver(self):
		if self.exp_approver and "Expense Approver" not in frappe.get_roles(self.exp_approver):
			frappe.throw(_("{0} ({1}) must have role 'Expense Approver'")\
				.format(get_fullname(self.exp_approver), self.exp_approver), InvalidExpenseApproverError)
	
	def update_task(self):
		task = frappe.get_doc("Task", self.task)
		task.update_total_expense_claim()
		task.save()

	def validate_task(self):
		if self.project and not self.task:
			frappe.throw(_("Task is mandatory if Expense Claim is against a Project"))

	def validate_sanctioned_amount(self):
		for d in self.get('expenses'):
			if flt(d.sanctioned_amount) > flt(d.claim_amount):
				frappe.throw(_("Sanctioned Amount cannot be greater than Claim Amount in Row {0}.").format(d.idx))
				

@frappe.whitelist()
def get_expense_approver(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql("""
		select u.name, concat(u.first_name, ' ', u.last_name) 
		from tabUser u, tabUserRole r
		where u.name = r.parent and r.role = 'Expense Approver' and u.name like %s
	""", ("%" + txt + "%"))