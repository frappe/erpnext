# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate
from erpnext.accounts.doctype.journal_entry.journal_entry import get_default_bank_cash_account

class EmployeeAdvanceOverPayment(frappe.ValidationError):
	pass

class EmployeeAdvance(Document):
	def onload(self):
		self.get("__onload").make_payment_via_journal_entry = frappe.db.get_single_value('Accounts Settings',
			'make_payment_via_journal_entry')

	def validate(self):
		self.set_status()
		self.validate_employee_advance_account()

	def on_cancel(self):
		self.set_status()

	def set_status(self):
		if self.docstatus == 0:
			self.status = "Draft"
		if self.docstatus == 1:
			if self.claimed_amount and flt(self.claimed_amount) == flt(self.paid_amount):
				self.status = "Claimed"
			elif self.paid_amount and self.advance_amount == flt(self.paid_amount):
				self.status = "Paid"
			else:
				self.status = "Unpaid"
		elif self.docstatus == 2:
			self.status = "Cancelled"

	def validate_employee_advance_account(self):
		company_currency = erpnext.get_company_currency(self.company)
		if (self.advance_account and
			company_currency != frappe.db.get_value('Account', self.advance_account, 'account_currency')):
			frappe.throw(_("Advance account currency should be same as company currency {0}")
				.format(company_currency))

	def set_total_advance_paid(self):
		paid_amount = frappe.db.sql("""
			select ifnull(sum(debit_in_account_currency), 0) as paid_amount
			from `tabGL Entry`
			where against_voucher_type = 'Employee Advance'
				and against_voucher = %s
				and party_type = 'Employee'
				and party = %s
		""", (self.name, self.employee), as_dict=1)[0].paid_amount

		return_amount = frappe.db.sql("""
			select name, ifnull(sum(credit_in_account_currency), 0) as return_amount
			from `tabGL Entry`
			where against_voucher_type = 'Employee Advance'
				and voucher_type != 'Expense Claim'
				and against_voucher = %s
				and party_type = 'Employee'
				and party = %s
		""", (self.name, self.employee), as_dict=1)[0].return_amount

		if flt(paid_amount) > self.advance_amount:
			frappe.throw(_("Row {0}# Paid Amount cannot be greater than requested advance amount"),
				EmployeeAdvanceOverPayment)

		if flt(return_amount) > self.paid_amount - self.claimed_amount:
			frappe.throw(_("Return amount cannot be greater unclaimed amount"))

		self.db_set("paid_amount", paid_amount)
		self.db_set("return_amount", return_amount)
		self.set_status()
		frappe.db.set_value("Employee Advance", self.name , "status", self.status)


	def update_claimed_amount(self):
		claimed_amount = frappe.db.sql("""
			SELECT sum(ifnull(allocated_amount, 0))
			FROM `tabExpense Claim Advance` eca, `tabExpense Claim` ec
			WHERE
				eca.employee_advance = %s
				AND ec.approval_status="Approved"
				AND ec.name = eca.parent
				AND ec.docstatus=1
				AND eca.allocated_amount > 0
		""", self.name)[0][0] or 0

		frappe.db.set_value("Employee Advance", self.name, "claimed_amount", flt(claimed_amount))
		self.reload()
		self.set_status()
		frappe.db.set_value("Employee Advance", self.name, "status", self.status)

@frappe.whitelist()
def get_due_advance_amount(employee, posting_date):
	employee_due_amount = frappe.get_all("Employee Advance", \
		filters = {"employee":employee, "docstatus":1, "posting_date":("<=", posting_date)}, \
		fields = ["advance_amount", "paid_amount"])
	return sum([(emp.advance_amount - emp.paid_amount) for emp in employee_due_amount])

@frappe.whitelist()
def make_bank_entry(dt, dn):
	doc = frappe.get_doc(dt, dn)
	payment_account = get_default_bank_cash_account(doc.company, account_type="Cash",
		mode_of_payment=doc.mode_of_payment)

	je = frappe.new_doc("Journal Entry")
	je.posting_date = nowdate()
	je.voucher_type = 'Bank Entry'
	je.company = doc.company
	je.remark = 'Payment against Employee Advance: ' + dn + '\n' + doc.purpose

	je.append("accounts", {
		"account": doc.advance_account,
		"debit_in_account_currency": flt(doc.advance_amount),
		"reference_type": "Employee Advance",
		"reference_name": doc.name,
		"party_type": "Employee",
		"party": doc.employee,
		"is_advance": "Yes"
	})

	je.append("accounts", {
		"account": payment_account.account,
		"credit_in_account_currency": flt(doc.advance_amount),
		"account_currency": payment_account.account_currency,
		"account_type": payment_account.account_type
	})

	return je.as_dict()

@frappe.whitelist()
def make_return_entry(employee, company, employee_advance_name,
		return_amount, advance_account, mode_of_payment=None):
	return_account = get_default_bank_cash_account(company, account_type='Cash', mode_of_payment = mode_of_payment)

	mode_of_payment_type = ''
	if mode_of_payment:
		mode_of_payment_type = frappe.get_cached_value('Mode of Payment', mode_of_payment, 'type')
		if mode_of_payment_type not in ["Cash", "Bank"]:
			# if mode of payment is General then it unset the type
			mode_of_payment_type = None

	je = frappe.new_doc('Journal Entry')
	je.posting_date = nowdate()
	# if mode of payment is Bank then voucher type is Bank Entry
	je.voucher_type = '{} Entry'.format(mode_of_payment_type) if mode_of_payment_type else 'Cash Entry'
	je.company = company
	je.remark = 'Return against Employee Advance: ' + employee_advance_name

	je.append('accounts', {
		'account': advance_account,
		'credit_in_account_currency': return_amount,
		'reference_type': 'Employee Advance',
		'reference_name': employee_advance_name,
		'party_type': 'Employee',
		'party': employee,
		'is_advance': 'Yes'
	})

	je.append("accounts", {
		"account": return_account.account,
		"debit_in_account_currency": return_amount,
		"account_currency": return_account.account_currency,
		"account_type": return_account.account_type
	})

	return je.as_dict()


