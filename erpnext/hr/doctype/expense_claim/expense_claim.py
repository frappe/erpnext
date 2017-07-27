# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import get_fullname, flt, cstr
from frappe.model.document import Document
from erpnext.hr.utils import set_employee_name
from erpnext.accounts.party import get_party_account
from erpnext.accounts.general_ledger import make_gl_entries
from erpnext.accounts.doctype.sales_invoice.sales_invoice import get_bank_cash_account
from erpnext.controllers.accounts_controller import AccountsController
from frappe.utils.csvutils import getlink

class InvalidExpenseApproverError(frappe.ValidationError): pass

class ExpenseClaim(AccountsController):
	def get_feed(self):
		return _("{0}: From {0} for {1}").format(self.approval_status,
			self.employee_name, self.total_claimed_amount)

	def validate(self):
		self.validate_sanctioned_amount()
		self.validate_expense_approver()
		self.calculate_total_amount()
		set_employee_name(self)
		self.set_expense_account()
		self.set_payable_account()
		self.set_cost_center()
		self.set_status()
		if self.task and not self.project:
			self.project = frappe.db.get_value("Task", self.task, "project")

	def set_status(self):
		self.status = {
			"0": "Draft",
			"1": "Submitted",
			"2": "Cancelled"
		}[cstr(self.docstatus or 0)]

		if self.total_sanctioned_amount > 0 and self.total_sanctioned_amount == self.total_amount_reimbursed \
			and self.docstatus == 1 and self.approval_status == 'Approved':
			self.status = "Paid"
		elif self.total_sanctioned_amount > 0 and self.docstatus == 1 and self.approval_status == 'Approved':
			self.status = "Unpaid"
		elif self.docstatus == 1 and self.approval_status == 'Rejected':
			self.status = 'Rejected'

	def set_payable_account(self):
		if not self.payable_account and not self.is_paid:
			self.payable_account = frappe.db.get_value("Company", self.company, "default_payable_account")

	def set_cost_center(self):
		if not self.cost_center:
			self.cost_center = frappe.db.get_value('Company', self.company, 'cost_center')

	def on_submit(self):
		if self.approval_status=="Draft":
			frappe.throw(_("""Approval Status must be 'Approved' or 'Rejected'"""))

		self.update_task_and_project()
		self.make_gl_entries()

		if self.is_paid:
			update_reimbursed_amount(self)

		self.set_status()

	def on_cancel(self):
		self.update_task_and_project()
		if self.payable_account:
			self.make_gl_entries(cancel=True)

		if self.is_paid:
			update_reimbursed_amount(self)

		self.set_status()

	def update_task_and_project(self):
		if self.task:
			self.update_task()
		elif self.project:
			frappe.get_doc("Project", self.project).update_project()

	def make_gl_entries(self, cancel = False):
		if flt(self.total_sanctioned_amount) > 0:
			gl_entries = self.get_gl_entries()
			make_gl_entries(gl_entries, cancel)

	def get_gl_entries(self):
		gl_entry = []
		self.validate_account_details()
		
		# payable entry
		gl_entry.append(
			self.get_gl_dict({
				"account": self.payable_account,
				"credit": self.total_sanctioned_amount,
				"credit_in_account_currency": self.total_sanctioned_amount,
				"against": ",".join([d.default_account for d in self.expenses]),
				"party_type": "Employee",
				"party": self.employee,
				"against_voucher_type": self.doctype,
				"against_voucher": self.name
			})
		)

		# expense entries
		for data in self.expenses:
			gl_entry.append(
				self.get_gl_dict({
					"account": data.default_account,
					"debit": data.sanctioned_amount,
					"debit_in_account_currency": data.sanctioned_amount,
					"against": self.employee,
					"cost_center": self.cost_center
				})
			)

		if self.is_paid:
			# payment entry
			payment_account = get_bank_cash_account(self.mode_of_payment, self.company).get("account")
			gl_entry.append(
				self.get_gl_dict({
					"account": payment_account,
					"credit": self.total_sanctioned_amount,
					"credit_in_account_currency": self.total_sanctioned_amount,
					"against": self.employee
				})
			)

			gl_entry.append(
				self.get_gl_dict({
					"account": self.payable_account,
					"party_type": "Employee",
					"party": self.employee,
					"against": payment_account,
					"debit": self.total_sanctioned_amount,
					"debit_in_account_currency": self.total_sanctioned_amount,
					"against_voucher": self.name,
					"against_voucher_type": self.doctype,
				})
			)

		return gl_entry

	def validate_account_details(self):
		if not self.cost_center:
			frappe.throw(_("Cost center is required to book an expense claim"))

		if not self.payable_account:
			frappe.throw(_("Please set default payable account for the company {0}").format(getlink("Company",self.company)))

		if self.is_paid:
			if not self.mode_of_payment:
				frappe.throw(_("Mode of payment is required to make a payment").format(self.employee))

	def calculate_total_amount(self):
		self.total_claimed_amount = 0
		self.total_sanctioned_amount = 0
		for d in self.get('expenses'):
			if self.approval_status == 'Rejected':
				d.sanctioned_amount = 0.0

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

	def validate_sanctioned_amount(self):
		for d in self.get('expenses'):
			if flt(d.sanctioned_amount) > flt(d.claim_amount):
				frappe.throw(_("Sanctioned Amount cannot be greater than Claim Amount in Row {0}.").format(d.idx))

	def set_expense_account(self):
		for expense in self.expenses:
			if not expense.default_account:
				expense.default_account = get_expense_claim_account(expense.expense_type, self.company)["account"]

def update_reimbursed_amount(doc):
	amt = frappe.db.sql("""select ifnull(sum(debit_in_account_currency), 0) as amt 
		from `tabGL Entry` where against_voucher_type = 'Expense Claim' and against_voucher = %s
		and party = %s """, (doc.name, doc.employee) ,as_dict=1)[0].amt

	doc.total_amount_reimbursed = amt
	frappe.db.set_value("Expense Claim", doc.name , "total_amount_reimbursed", amt)

	doc.set_status()
	frappe.db.set_value("Expense Claim", doc.name , "status", doc.status)

@frappe.whitelist()
def get_expense_approver(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql("""
		select u.name, concat(u.first_name, ' ', u.last_name)
		from tabUser u, `tabHas Role` r
		where u.name = r.parent and r.role = 'Expense Approver' 
		and u.enabled = 1 and u.name like %s
	""", ("%" + txt + "%"))

@frappe.whitelist()
def make_bank_entry(docname):
	from erpnext.accounts.doctype.journal_entry.journal_entry import get_default_bank_cash_account

	expense_claim = frappe.get_doc("Expense Claim", docname)
	default_bank_cash_account = get_default_bank_cash_account(expense_claim.company, "Bank")
	if not default_bank_cash_account:
		default_bank_cash_account = get_default_bank_cash_account(expense_claim.company, "Cash")

	je = frappe.new_doc("Journal Entry")
	je.voucher_type = 'Bank Entry'
	je.company = expense_claim.company
	je.remark = 'Payment against Expense Claim: ' + docname;

	je.append("accounts", {
		"account": expense_claim.payable_account,
		"debit_in_account_currency": flt(expense_claim.total_sanctioned_amount - expense_claim.total_amount_reimbursed),
		"reference_type": "Expense Claim",
		"party_type": "Employee",
		"party": expense_claim.employee,
		"reference_name": expense_claim.name
	})

	je.append("accounts", {
		"account": default_bank_cash_account.account,
		"credit_in_account_currency": flt(expense_claim.total_sanctioned_amount - expense_claim.total_amount_reimbursed),
		"reference_type": "Expense Claim",
		"reference_name": expense_claim.name,
		"balance": default_bank_cash_account.balance,
		"account_currency": default_bank_cash_account.account_currency,
		"account_type": default_bank_cash_account.account_type
	})

	return je.as_dict()

@frappe.whitelist()
def get_expense_claim_account(expense_claim_type, company):
	account = frappe.db.get_value("Expense Claim Account",
		{"parent": expense_claim_type, "company": company}, "default_account")
	
	if not account:
		frappe.throw(_("Please set default account in Expense Claim Type {0}")
			.format(expense_claim_type))
	
	return {
		"account": account
	}