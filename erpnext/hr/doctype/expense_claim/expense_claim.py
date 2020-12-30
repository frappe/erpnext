# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe import _
from frappe.utils import get_fullname, flt, cstr, get_link_to_form
from frappe.model.document import Document
from erpnext.hr.utils import set_employee_name
from erpnext.accounts.party import get_party_account
from erpnext.accounts.general_ledger import make_gl_entries
from erpnext.accounts.doctype.sales_invoice.sales_invoice import get_bank_cash_account
from erpnext.controllers.buying_controller import BuyingController
from frappe.utils.csvutils import getlink
from erpnext.accounts.utils import get_account_currency

class InvalidExpenseApproverError(frappe.ValidationError): pass
class ExpenseApproverIdentityError(frappe.ValidationError): pass

class ExpenseClaim(BuyingController):
	def onload(self):
		self.get("__onload").make_payment_via_journal_entry = frappe.db.get_single_value('Accounts Settings',
			'make_payment_via_journal_entry')

	def validate(self):
		self.validate_advances()
		self.validate_sanctioned_amount()
		self.calculate_total_amount()
		self.set_amounts_in_company_currency()
		set_employee_name(self)
		self.set_expense_account(validate=True)
		self.set_payable_account()
		self.set_cost_center()
		self.set_grand_total_and_outstanding_amount()
		self.set_status()
		if self.task and not self.project:
			self.project = frappe.db.get_value("Task", self.task, "project")

	def set_status(self):
		if self.is_new():
			if self.get("amended_from"):
				self.status = "Draft"
			return

		precision = self.precision("outstanding_amount")
		outstanding_amount = flt(self.outstanding_amount, precision)

		if self.docstatus == 2:
			self.status = "Cancelled"
		elif self.docstatus == 1:
			if self.approval_status == "Approved":
				if self.is_paid or outstanding_amount <= 0:
					self.status = "Paid"
				elif outstanding_amount > 0:
					self.status = "Unpaid"
				else:
					self.status = "Submitted"
			elif self.approval_status == "Rejected":
				self.status = "Rejected"
		else:
			self.status = "Draft"

	def set_payable_account(self):
		if not self.payable_account and not self.is_paid:
			self.payable_account = frappe.get_cached_value('Company', self.company, 'default_expense_claim_payable_account')

	def set_cost_center(self):
		if not self.cost_center:
			self.cost_center = frappe.get_cached_value('Company', self.company, 'cost_center')

	def on_submit(self):
		if self.approval_status=="Draft":
			frappe.throw(_("""Approval Status must be 'Approved' or 'Rejected'"""))

		self.update_task_and_project()
		self.make_gl_entries()

		if self.is_paid:
			update_reimbursed_amount(self)

		self.set_status()
		self.update_claimed_amount_in_employee_advance()

	def on_cancel(self):
		self.update_task_and_project()
		self.ignore_linked_doctypes = ('GL Entry', 'Stock Ledger Entry')
		if self.payable_account:
			self.make_gl_entries(cancel=True)

		if self.is_paid:
			update_reimbursed_amount(self)

		self.set_status()
		self.update_claimed_amount_in_employee_advance()

	def update_claimed_amount_in_employee_advance(self):
		for d in self.get("advances"):
			frappe.get_doc("Employee Advance", d.employee_advance).update_claimed_amount()

	def update_task_and_project(self):
		if self.task:
			self.update_task()
		elif self.project:
			frappe.get_doc("Project", self.project).update_project()

	def make_gl_entries(self, cancel=False):
		if flt(self.total) > 0:
			gl_entries = self.get_gl_entries()
			make_gl_entries(gl_entries, cancel)

	def get_gl_entries(self):
		gl_entry = []
		self.validate_account_details()
		payable_account_currency = get_account_currency(self.payable_account)

		# payable entry
		if self.grand_total:
			gl_entry.append(
				self.get_gl_dict({
					"account": self.payable_account,
					"credit": self.outstanding_amount,
					"credit_in_account_currency": self.outstanding_amount,
					"against": ",".join([d.default_account for d in self.items]),
					"party_type": "Employee",
					"party": self.employee,
					"against_voucher_type": self.doctype,
					"against_voucher": self.name,
					"cost_center": self.cost_center
				}, item=self)
			)

		# expense entries
		for data in self.items:
			account_currency = get_account_currency(data.default_account)
			gl_entry.append(
				self.get_gl_dict({
					"account": data.default_account,
					"debit": data.base_amount,
					"debit_in_account_currency": (data.base_amount
						if account_currency == self.company_currency else data.amount),
					"against": self.employee,
					"cost_center": data.cost_center or self.cost_center
				}, item=data)
			)

		for data in self.advances:
			gl_entry.append(
				self.get_gl_dict({
					"account": data.advance_account,
					"credit": data.allocated_amount,
					"credit_in_account_currency": data.allocated_amount,
					"against": ",".join([d.default_account for d in self.items]),
					"party_type": "Employee",
					"party": self.employee,
					"against_voucher_type": "Employee Advance",
					"against_voucher": data.employee_advance
				})
			)

		self.add_tax_gl_entries(gl_entry)

		if self.is_paid and self.grand_total:
			# payment entry
			payment_account = get_bank_cash_account(self.mode_of_payment, self.company).get("account")
			account_currency = get_account_currency(payment_account)
			gl_entry.append(
				self.get_gl_dict({
					"account": payment_account,
					"credit": self.outstanding_amount,
					"credit_in_account_currency": self.outstanding_amount,
					"against": self.employee
				}, item=self)
			)

			gl_entry.append(
				self.get_gl_dict({
					"account": self.payable_account,
					"party_type": "Employee",
					"party": self.employee,
					"against": payment_account,
					"debit": self.outstanding_amount,
					"debit_in_account_currency": self.outstanding_amount,
					"against_voucher": self.name,
					"against_voucher_type": self.doctype,
				}, item=self)
			)

		return gl_entry

	def add_tax_gl_entries(self, gl_entries):
		# tax table gl entries
		for tax in self.get("taxes"):
			account_currency = get_account_currency(tax.account_head)
			dr_or_cr = "debit" if tax.add_deduct_tax == "Add" else "credit"

			gl_entries.append(
				self.get_gl_dict({
					"account": tax.account_head,
					"against": self.employee,
					dr_or_cr: tax.base_tax_amount,
					dr_or_cr + "_in_account_currency": tax.base_tax_amount \
						if account_currency == self.company_currency \
						else tax.tax_amount,
					"cost_center": tax.cost_center,
					"against_voucher_type": self.doctype,
					"against_voucher": self.name
				}, account_currency, item=tax)
			)

	def validate_account_details(self):
		for data in self.items:
			if not data.cost_center:
				frappe.throw(_("Row {0}: {1} is required in the items table to book an expense claim.")
					.format(data.idx, frappe.bold("Cost Center")))

		if self.is_paid:
			if not self.mode_of_payment:
				frappe.throw(_("Mode of payment is required to make a payment").format(self.employee))

	def calculate_total_amount(self):
		self.total_claimed_amount = 0
		for d in self.get('items'):
			if self.approval_status == 'Rejected':
				d.amount = 0.0

			self.total_claimed_amount += flt(d.claimed_amount)

	def set_amounts_in_company_currency(self):
		"""set values in base currency"""
		fields = ["total_claimed_amount", "total_amount_reimbursed", "total"]
		for f in fields:
			val = flt(flt(self.get(f), self.precision(f)) * self.conversion_rate, self.precision("base_" + f))
			self.set("base_" + f, val)

	def set_grand_total_and_outstanding_amount(self):
		self.grand_total = flt(self.total) + flt(self.total_taxes_and_charges)
		self.outstanding_amount = flt(self.base_grand_total) - flt(self.total_advance_amount) - flt(self.base_total_amount_reimbursed)

	def update_task(self):
		task = frappe.get_doc("Task", self.task)
		task.update_total_expense_claim()
		task.save()

	def validate_advances(self):
		self.total_advance_amount = 0
		for d in self.get("advances"):
			ref_doc = frappe.db.get_value("Employee Advance", d.employee_advance,
				["posting_date", "paid_amount", "claimed_amount", "advance_account",
				"currency", "exchange_rate"], as_dict=1)

			paid_amount = flt(ref_doc.paid_amount) * flt(ref_doc.exchange_rate)
			claimed_amount = flt(ref_doc.claimed_amount) * flt(ref_doc.exchange_rate)

			d.posting_date = ref_doc.posting_date
			d.advance_account = ref_doc.advance_account
			d.advance_paid = paid_amount
			d.unclaimed_amount = paid_amount - claimed_amount

			if d.allocated_amount and flt(d.allocated_amount) > flt(d.unclaimed_amount):
				frappe.throw(_("Row {0}# Allocated amount {1} cannot be greater than unclaimed amount {2}")
					.format(d.idx, d.allocated_amount, d.unclaimed_amount))

			self.total_advance_amount += flt(d.allocated_amount)

		if self.total_advance_amount:
			precision = self.precision("total_advance_amount")
			if flt(self.total_advance_amount, precision) > flt(self.base_total_claimed_amount, precision):
				frappe.throw(_("Total advance amount cannot be greater than total claimed amount"))

			if self.total \
					and flt(self.total_advance_amount, precision) > flt(self.base_total, precision):
				frappe.throw(_("Total advance amount cannot be greater than total sanctioned amount"))

	def validate_sanctioned_amount(self):
		for d in self.get('items'):
			if flt(d.amount) > flt(d.claimed_amount):
				frappe.throw(_("Sanctioned Amount cannot be greater than Claim Amount in Row {0}.").format(d.idx))

	def set_expense_account(self, validate=False):
		for expense in self.items:
			if not expense.default_account or not validate:
				expense.default_account = get_expense_claim_account(expense.item_code, self.company)["account"]

def update_reimbursed_amount(doc, jv=None):
	condition = ""

	if jv:
		condition += "and voucher_no = '{0}'".format(jv)

	amt = frappe.db.sql("""select ifnull(sum(debit_in_account_currency), 0) - ifnull(sum(credit_in_account_currency), 0)as amt
		from `tabGL Entry` where against_voucher_type = 'Expense Claim' and against_voucher = %s
		and party = %s {condition}""".format(condition=condition), #nosec
		(doc.name, doc.employee) ,as_dict=1)[0].amt

	doc.db_set("total_amount_reimbursed", amt)
	doc.set_amounts_in_company_currency()
	doc.set_status()
	doc.db_set("status", doc.status)

@frappe.whitelist()
def make_bank_entry(dt, dn):
	from erpnext.accounts.doctype.journal_entry.journal_entry import get_default_bank_cash_account

	expense_claim = frappe.get_doc(dt, dn)
	default_bank_cash_account = get_default_bank_cash_account(expense_claim.company, "Bank")
	if not default_bank_cash_account:
		default_bank_cash_account = get_default_bank_cash_account(expense_claim.company, "Cash")

	payable_amount = flt(expense_claim.total) \
		- flt(expense_claim.total_amount_reimbursed) - flt(expense_claim.total_advance_amount)

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
		"cost_center": erpnext.get_default_cost_center(expense_claim.company),
		"reference_name": expense_claim.name
	})

	je.append("accounts", {
		"account": default_bank_cash_account.account,
		"credit_in_account_currency": payable_amount,
		"reference_type": "Expense Claim",
		"reference_name": expense_claim.name,
		"balance": default_bank_cash_account.balance,
		"account_currency": default_bank_cash_account.account_currency,
		"cost_center": erpnext.get_default_cost_center(expense_claim.company),
		"account_type": default_bank_cash_account.account_type
	})

	return je.as_dict()

@frappe.whitelist()
def get_expense_claim_account_and_cost_center(item_code, company):
	data = get_expense_claim_account(item_code, company)
	cost_center = erpnext.get_default_cost_center(company)

	return {
		"account": data.get("account"),
		"cost_center": cost_center
	}

@frappe.whitelist()
def get_expense_claim_account(item_code, company):
	account = frappe.db.get_value("Item Default",
		{"parent": item_code, "company": company}, "expense_account")
	if not account:
		frappe.throw(_("Set the Default Expense Account for the {0} {1}")
			.format(frappe.bold("Item"), get_link_to_form("Item", item_code)))

	return {
		"account": account
	}

@frappe.whitelist()
def get_advances(employee, advance_id=None):
	if not advance_id:
		condition = 'docstatus=1 and employee={0} and paid_amount > 0 and paid_amount > claimed_amount + return_amount'.format(frappe.db.escape(employee))
	else:
		condition = 'name={0}'.format(frappe.db.escape(advance_id))

	return frappe.db.sql("""
		select
			name, currency, exchange_rate, posting_date, paid_amount, claimed_amount, advance_account
		from
			`tabEmployee Advance`
		where {0}
	""".format(condition), as_dict=1)


@frappe.whitelist()
def get_expense_claim(
	employee_name, company, employee_advance_name, posting_date, paid_amount, claimed_amount):
	default_payable_account = frappe.get_cached_value('Company',  company,  "default_payable_account")
	default_cost_center = frappe.get_cached_value('Company',  company,  'cost_center')

	expense_claim = frappe.new_doc('Expense Claim')
	expense_claim.company = company
	expense_claim.employee = employee_name
	expense_claim.payable_account = default_payable_account
	expense_claim.cost_center = default_cost_center
	expense_claim.is_paid = 1 if flt(paid_amount) else 0
	expense_claim.append(
		'advances',
		{
			'employee_advance': employee_advance_name,
			'posting_date': posting_date,
			'advance_paid': flt(paid_amount),
			'unclaimed_amount': flt(paid_amount) - flt(claimed_amount),
			'allocated_amount': flt(paid_amount) - flt(claimed_amount)
		}
	)

	return expense_claim
