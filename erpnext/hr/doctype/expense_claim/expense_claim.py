# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, cstr, cint
from erpnext.hr.utils import set_employee_name
from erpnext.accounts.general_ledger import make_gl_entries
from erpnext.accounts.utils import unlink_ref_doc_from_payment_entries
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.hr.doctype.employee_advance.employee_advance import get_unclaimed_advances

class InvalidExpenseApproverError(frappe.ValidationError): pass
class ExpenseApproverIdentityError(frappe.ValidationError): pass

class ExpenseClaim(AccountsController):
	def onload(self):
		self.get("__onload").make_payment_via_journal_entry = frappe.db.get_single_value('Accounts Settings',
			'make_payment_via_journal_entry')

	def set_title(self):
		self.title = self.employee_name or self.employee

	def validate(self):
		self.set_cost_center()
		self.set_project_from_task()
		self.validate_sanctioned_amount()
		self.validate_employee_advances()
		self.calculate_totals()
		self.validate_outstanding_amount()
		set_employee_name(self)
		self.validate_expense_account(for_validate=True)
		self.validate_purchase_invoices(for_validate=True)

		if cint(self.allocate_advances_automatically):
			self.set_advances()
		self.clear_unallocated_advances("Expense Claim Advance", "advances")

		self.set_status()

	def on_submit(self):
		if self.approval_status=="Draft":
			frappe.throw(_("""Approval Status must be 'Approved' or 'Rejected'"""))

		self.validate_expense_account()
		self.validate_purchase_invoices()
		self.update_task_and_project()
		self.make_gl_entries()

		self.update_against_document_in_jv()
		self.update_claimed_amount_in_employee_advance()

	def on_cancel(self):
		self.update_task_and_project()
		self.make_gl_entries(cancel=True)

		self.update_claimed_amount_in_employee_advance()
		unlink_ref_doc_from_payment_entries(self, validate_permission=True)

		self.set_status()

	def set_advances(self):
		self.set("advances", [])

		res = self.get_advance_entries()
		employee_advances = get_unclaimed_advances(self.employee, self.payable_account)

		total_allocatable = 0
		total_advance_allocated = 0
		project_wise_allocatable = {}
		project_wise_allocated = {}
		for d in self.expenses:
			project_wise_allocatable.setdefault(cstr(d.project), 0)
			project_wise_allocatable[cstr(d.project)] += flt(d.sanctioned_amount)
			total_allocatable += flt(d.sanctioned_amount)

		for d in employee_advances:
			project_allocatable = project_wise_allocatable.get(cstr(d.project), 0)
			project_allocated = project_wise_allocated.get(cstr(d.project), 0)
			allocated_amount = min(project_allocatable - project_allocated, total_allocatable - total_advance_allocated,
				d.advance_amount)

			project_wise_allocated.setdefault(cstr(d.project), 0)
			project_wise_allocated[cstr(d.project)] += flt(allocated_amount)
			total_advance_allocated += flt(allocated_amount)

			self.append("advances", {
				"reference_type": d.reference_type,
				"reference_name": d.reference_name,
				"advance_date": d.posting_date,
				"remarks": d.remarks,
				"project": d.project,
				"advance_amount": flt(d.advance_amount),
				"allocated_amount": allocated_amount
			})

		for d in res:
			self.append("advances", {
				"reference_type": d.reference_type,
				"reference_name": d.reference_name,
				"reference_row": d.reference_row,
				"advance_date": d.posting_date,
				"remarks": d.remarks,
				"advance_amount": flt(d.amount),
				"allocated_amount": 0
			})

	def set_cost_center(self):
		default_cost_center = self.get('cost_center') or frappe.get_cached_value('Company', self.company, 'cost_center')
		for d in self.expenses:
			if d.expense_account and not d.cost_center:
				report_type = frappe.get_cached_value("Account", d.expense_account, "report_type")
				if report_type == "Profit and Loss":
					d.cost_center = default_cost_center

	def set_project_from_task(self):
		for d in self.expenses:
			if d.task and not d.project:
				d.project = frappe.db.get_value("Task", d.task, "project", cache=1)

	def update_claimed_amount_in_employee_advance(self):
		for d in self.advances:
			if d.reference_type == "Employee Advance":
				frappe.get_doc("Employee Advance", d.reference_name).update_claimed_amount()

	def update_task_and_project(self):
		projects = []
		tasks = []

		for d in self.expenses:
			if d.project:
				projects.append(d.project)
			if d.task:
				tasks.append(d.tasks)

		projects = set(projects)
		for project in projects:
			frappe.get_doc("Project", project).update_project()

		tasks = set(tasks)
		for task in tasks:
			task = frappe.get_doc("Task", task)
			task.update_total_expense_claim()
			task.save()

	def make_gl_entries(self, cancel=False):
		if flt(self.total_sanctioned_amount) > 0:
			gl_entries = self.get_gl_entries()
			make_gl_entries(gl_entries, cancel)

	def get_gl_entries(self):
		self.validate_account_details()

		gl_entry = []
		total_employee_advances = sum([d.allocated_amount for d in self.advances if d.reference_type == "Employee Advance"])
		total_employee_advances = flt(total_employee_advances, self.precision('total_advance'))
		payable_amount = flt(self.total_sanctioned_amount) - total_employee_advances

		# payable entry
		if payable_amount:
			gl_entry.append(
				self.get_gl_dict({
					"account": self.payable_account,
					"credit": payable_amount,
					"credit_in_account_currency": payable_amount,
					"against": ", ".join(set([exp.expense_account for exp in self.expenses])),
					"party_type": "Employee",
					"party": self.employee,
					"cost_center": self.get('cost_center')
				})
			)

		# expense entries
		for d in self.expenses:
			gl_entry.append(
				self.get_gl_dict({
					"account": d.expense_account,
					"debit": d.sanctioned_amount,
					"debit_in_account_currency": d.sanctioned_amount,
					"against": self.employee,
					"cost_center": d.cost_center,
					"project": d.project,
					"party_type": d.party_type,
					"party": d.party,
					"against_voucher_type": "Purchase Invoice" if d.requires_purchase_invoice else "",
					"against_voucher": d.purchase_invoice if d.requires_purchase_invoice else "",
				})
			)

		for d in self.advances:
			if d.reference_type == "Employee Advance":
				gl_entry.append(
					self.get_gl_dict({
						"account": self.payable_account,
						"credit": d.allocated_amount,
						"credit_in_account_currency": d.allocated_amount,
						"against": ", ".join(set([exp.expense_account for exp in self.expenses])),
						"party_type": "Employee",
						"party": self.employee,
						"against_voucher_type": "Employee Advance",
						"against_voucher": d.reference_name,
						"project": d.project
					})
				)

		return gl_entry

	def validate_account_details(self):
		payable_amount = flt(self.total_sanctioned_amount) - flt(self.total_advance)
		if payable_amount and not self.payable_account:
			frappe.throw(_("Payable Account is mandatory"))

	def calculate_totals(self):
		self.total_claimed_amount = 0
		self.total_sanctioned_amount = 0
		self.total_advance = 0
		self.total_amount_reimbursed = 0

		for d in self.get('expenses'):
			if self.approval_status == 'Rejected':
				d.sanctioned_amount = 0.0

			self.round_floats_in(d, ['claim_amount', 'sanctioned_amount'])
			self.total_claimed_amount += d.claim_amount
			self.total_sanctioned_amount += d.sanctioned_amount

		for d in self.get('advances'):
			if self.approval_status == 'Rejected':
				d.allocated_amount = 0

			self.round_floats_in(d, ['allocated_amount'])
			self.total_advance += d.allocated_amount

		self.round_floats_in(self, ["total_claimed_amount", "total_sanctioned_amount", "total_advance",
			"total_amount_reimbursed"])
		self.outstanding_amount = flt(self.total_sanctioned_amount - self.total_amount_reimbursed - self.total_advance,
			self.precision("outstanding_amount"))

	def validate_employee_advances(self):
		for d in self.advances:
			if d.reference_type == "Employee Advance":
				ref_doc = frappe.db.get_value("Employee Advance", d.reference_name,
					["advance_account", "employee", "paid_amount", "balance_amount"], as_dict=1)

				if ref_doc.advance_account != self.payable_account:
					frappe.throw(_("Row #{0}: Advance Account {1} in Employee Advance {2} does not match the Expense Claim's Payable Account {3}")
						.format(d.idx, ref_doc.advance_account, d.reference_name, self.payable_account))
				if ref_doc.employee != self.employee:
					frappe.throw(_("Row #{0}: Employee {1} in Employee Advance {2} is not the same as {3} in Expense Claim")
						.format(d.idx, ref_doc.employee, d.reference_name, self.employee))

				d.paid_amount = ref_doc.paid_amount
				d.advance_amount = flt(ref_doc.balance_amount)

				if d.allocated_amount and flt(d.allocated_amount) > flt(d.advance_amount):
					frappe.throw(_("Row #{0}: Allocated Amount {1} cannot be greater than the Unclaimed Amount {2}")
						.format(d.idx, d.allocated_amount, d.advance_amount))

	def validate_outstanding_amount(self):
		if self.total_advance:
			precision = self.precision("total_advance")
			if self.total_sanctioned_amount and flt(self.total_advance, precision) > flt(self.total_sanctioned_amount, precision):
				frappe.throw(_("Total Advance Amount cannot be greater than the Total Sanctioned Amount"))

		if flt(self.outstanding_amount) < 0:
			frappe.throw(_("Outstanding amount cannot be less than 0"))

	def validate_sanctioned_amount(self):
		for d in self.get('expenses'):
			if flt(d.sanctioned_amount) > flt(d.claim_amount):
				frappe.throw(_("Sanctioned Amount cannot be greater than Claim Amount in Row {0}.").format(d.idx))

	def validate_expense_account(self, for_validate=False):
		for expense in self.expenses:
			if not cint(expense.requires_purchase_invoice) and not expense.expense_account:
				expense.expense_account = get_expense_claim_account(expense.expense_type, self.company)

			if not for_validate and not expense.expense_account:
				frappe.throw(_('Row #{0}: Please set Expense Account').format(expense.idx))

	def validate_purchase_invoices(self, for_validate=False):
		for expense in self.expenses:
			if cint(expense.requires_purchase_invoice):
				if not expense.purchase_invoice:
					frappe.throw(_("Row #{0}: Purchase Invoice must be selected for Expense Claim Type {1}")
						.format(expense.idx, expense.expense_type))

				details = get_purchase_invoice_details(expense.purchase_invoice)
				expense.expense_account = details.account
				expense.party_type = details.party_type
				expense.party = details.party

				if not for_validate:
					pi = frappe.db.get_value("Purchase Invoice", expense.purchase_invoice, ["docstatus", "outstanding_amount"], as_dict=1)
					if pi.docstatus != 1:
						frappe.throw(_("Row #{0}: Purchase Invoice {1} is not submitted.").format(expense.idx, expense.purchase_invoice))
					if flt(expense.sanctioned_amount) > flt(pi.outstanding_amount):
						frappe.throw(_("Row #{0}: Sanctioned Amount cannot be greater than the Outstanding Amount {1} of Purchase Invoice {2}")
							.format(expense.idx, pi.outstanding_amount, expense.purchase_invoice))
			else:
				expense.purchase_invoice = ""
				expense.party_type = ""
				expense.party = ""

def update_reimbursed_amount(doc):
	paid_amount_excl_employee_advance = frappe.db.sql("""
		select ifnull(sum(debit_in_account_currency - credit_in_account_currency), 0)
		from `tabGL Entry`
		where against_voucher_type = 'Expense Claim' and against_voucher = %s
			and party_type = 'Employee' and party = %s
	""", (doc.name, doc.employee))[0][0]

	advance_amound_excl_employee_advance = frappe.db.sql("""
		select ifnull(sum(allocated_amount), 0)
		from `tabExpense Claim Advance`
		where parent = %s and reference_type != 'Employee Advance'
	""", doc.name)[0][0]

	doc.total_amount_reimbursed = flt(paid_amount_excl_employee_advance - advance_amound_excl_employee_advance, doc.precision('total_amount_reimbursed'))
	doc.set_status()
	frappe.db.set_value(doc.doctype, doc.name, {
		'total_amount_reimbursed': doc.total_amount_reimbursed,
		'status': doc.status
	}, None)

@frappe.whitelist()
def make_bank_entry(dt, dn):
	from erpnext.accounts.doctype.journal_entry.journal_entry import get_default_bank_cash_account

	expense_claim = frappe.get_doc(dt, dn)
	default_bank_cash_account = get_default_bank_cash_account(expense_claim.company, "Bank")
	if not default_bank_cash_account:
		default_bank_cash_account = get_default_bank_cash_account(expense_claim.company, "Cash")

	payable_amount = flt(expense_claim.outstanding_amount)
	je = frappe.new_doc("Journal Entry")
	je.voucher_type = 'Bank Entry'
	je.company = expense_claim.company
	je.remark = 'Payment against Expense Claim: ' + dn

	je.append("accounts", {
		"account": expense_claim.payable_account,
		"debit_in_account_currency": payable_amount,
		"reference_type": "Expense Claim",
		"party_type": "Employee",
		"party": expense_claim.employee,
		"reference_name": expense_claim.name
	})

	je.append("accounts", {
		"account": default_bank_cash_account.account,
		"credit_in_account_currency": payable_amount,
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

	return account

@frappe.whitelist()
def get_purchase_invoice_details(purchase_invoice):
	details = frappe.db.get_value("Purchase Invoice", purchase_invoice,
		["supplier", "credit_to", "letter_of_credit", "project"], as_dict=1)
	if not details:
		frappe.throw(_("Invalid Purchase Invoice {0}").format(purchase_invoice))

	return frappe._dict({
		"account": details.credit_to,
		"party_type": "Letter of Credit" if details.letter_of_credit else "Supplier",
		"party": details.letter_of_credit or details.supplier,
		"project": details.project
	})


@frappe.whitelist()
def get_expense_claim(dt, dn):
	doc = frappe.get_doc(dt, dn)
	default_payable_account = frappe.get_cached_value('Company',  doc.company,  "default_expense_claim_payable_account")

	expense_claim = frappe.new_doc('Expense Claim')
	expense_claim.company = doc.company
	expense_claim.employee = doc.get("employee")
	expense_claim.payable_account = doc.get("advance_account") or default_payable_account
	expense_claim.append('advances', {
		'reference_type': 'Employee Advance',
		'reference_name': doc.name,
		'paid_amount': flt(doc.paid_amount),
		'remarks': doc.get('remarks') or doc.get('purpose'),
		'advance_amount': flt(doc.balance_amount),
		'allocated_amount': flt(doc.balance_amount),
		'advance_date': doc.get('advance_date') or doc.get('posting_date') or doc.get('transaction_date')
	})

	return expense_claim
