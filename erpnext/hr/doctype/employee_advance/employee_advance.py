# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate
from erpnext.accounts.doctype.journal_entry.journal_entry import get_default_bank_cash_account
from erpnext.payroll.doctype.salary_structure_assignment.salary_structure_assignment import get_employee_currency

class EmployeeAdvanceOverPayment(frappe.ValidationError):
	pass

class EmployeeAdvance(Document):
	def onload(self):
		self.get("__onload").make_payment_via_journal_entry = frappe.db.get_single_value('Accounts Settings',
			'make_payment_via_journal_entry')

	def validate(self):
		self.set_status()

	def on_cancel(self):
		self.ignore_linked_doctypes = ('GL Entry')
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

	def set_total_advance_paid(self):
		paid_amount_in_company_currency = frappe.db.sql("""
			select select ifnull(sum(debit_in_company_currency), 0) as paid_amount
			from `tabGL Entry`
			where against_voucher_type = 'Employee Advance'
				and against_voucher = %s
				and party_type = 'Employee'
				and party = %s
		""", (self.name, self.employee), as_dict=1)[0].paid_amount

		return_amount_in_company_currency = frappe.db.sql("""
			select ifnull(sum(credit_in_company_currency), 0) as return_amount
			from `tabGL Entry`
			where against_voucher_type = 'Employee Advance'
				and voucher_type != 'Expense Claim'
				and against_voucher = %s
				and party_type = 'Employee'
				and party = %s
		""", (self.name, self.employee), as_dict=1)[0].return_amount

		paid_amount = flt(paid_amount_in_company_currency) / flt(self.exchange_rate)
		return_amount = flt(return_amount_in_company_currency) / flt(self.exchange_rate)

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
def get_pending_amount(employee, posting_date):
	employee_curency = get_employee_currency(employee)
	employee_due_amount = frappe.get_all("Employee Advance", \
		filters = {"employee":employee, "docstatus":1, "posting_date":("<=", posting_date)}, \
		fields = ["advance_amount", "paid_amount"])
	pending_amount = sum([(emp.advance_amount - emp.paid_amount) for emp in employee_due_amount])
	return {
		'pending_amount': pending_amount,
		'employee_currency': employee_curency
	}
	

@frappe.whitelist()
def make_bank_entry(dt, dn):
	doc = frappe.get_doc(dt, dn)
	payment_account = get_default_bank_cash_account(doc.company, account_type="Cash",
		mode_of_payment=doc.mode_of_payment)
	if not payment_account:
		frappe.throw(_("Please set a Default Cash Account in Company defaults"))

	advance_account_currency = frappe.db.get_value('Account', doc.advance_account, 'account_currency')

	if advance_account_currency != doc.currency:
		advance_amount = flt(doc.advance_amount) * flt(doc.exchange_rate)
		advance_exchange_rate = 1
	else:
		advance_amount = doc.advance_amount
		advance_exchange_rate = doc.exchange_rate

	if payment_account.account_currency != doc.currency:
		paying_amount = flt(doc.advance_amount) * flt(doc.exchange_rate)
		paying_exchange_rate = 1
	else:
		paying_amount = doc.advance_amount
		paying_exchange_rate = doc.exchange_rate

	multi_currency = 0
	if advance_account_currency != payment_account.account_currency:
		multi_currency = 1

	je = frappe.new_doc("Journal Entry")
	je.posting_date = nowdate()
	je.voucher_type = 'Bank Entry'
	je.company = doc.company
	je.remark = 'Payment against Employee Advance: ' + dn + '\n' + doc.purpose
	je.multi_currency = multi_currency

	je.append("accounts", {
		"account": doc.advance_account,
		"account_currency": advance_account_currency,
		"exchange_rate": flt(advance_exchange_rate),
		"debit_in_account_currency": flt(advance_amount),
		"reference_type": "Employee Advance",
		"reference_name": doc.name,
		"party_type": "Employee",
		"cost_center": erpnext.get_default_cost_center(doc.company),
		"party": doc.employee,
		"is_advance": "Yes"
	})

	je.append("accounts", {
		"account": payment_account.account,
		"cost_center": erpnext.get_default_cost_center(doc.company),
		"credit_in_account_currency": flt(paying_amount),
		"account_currency": payment_account.account_currency,
		"account_type": payment_account.account_type,
		"exchange_rate": flt(paying_exchange_rate)
	})

	return je.as_dict()

@frappe.whitelist()
def create_return_through_additional_salary(doc):
	import json
	doc = frappe._dict(json.loads(doc))
	additional_salary = frappe.new_doc('Additional Salary')
	additional_salary.employee = doc.employee
	additional_salary.currency = doc.currency
	additional_salary.amount = doc.paid_amount - doc.claimed_amount
	additional_salary.company = doc.company
	additional_salary.ref_doctype = doc.doctype
	additional_salary.ref_docname = doc.name

	return additional_salary

@frappe.whitelist()
def make_return_entry(employee, company, employee_advance_name, return_amount,  advance_account, mode_of_payment=None):
	return_account = get_default_bank_cash_account(company, account_type='Cash', mode_of_payment = mode_of_payment)
	if not return_account:
		frappe.throw(_("Please set a Default Cash Account in Company defaults"))
	
	advance_account_currency = frappe.db.get_value('Account', advance_account, 'account_currency')

	employee_advance_doc = frappe.get_doc("Employee Advance", employee_advance_name)
	
	if advance_account_currency != employee_advance_doc.currency:
		advance_amount = flt(return_amount) * flt(employee_advance_doc.exchange_rate)
		advance_exchange_rate = 1
	else:
		advance_amount = return_amount
		advance_exchange_rate = employee_advance_doc.exchange_rate

	if return_account.account_currency != employee_advance_doc.currency:
		returning_amount = flt(return_amount) * flt(employee_advance_doc.exchange_rate)
		returning_exchange_rate = 1
	else:
		returning_amount = return_amount
		returning_exchange_rate = employee_advance_doc.exchange_rate

	multi_currency = 0
	if advance_account_currency != return_account.account_currency:
		multi_currency = 1

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
	je.multi_currency = multi_currency

	je.append('accounts', {
		'account': advance_account,
		'credit_in_account_currency': advance_amount,
		'account_currency': advance_account_currency,
		'exchange_rate': advance_exchange_rate,
		'reference_type': 'Employee Advance',
		'reference_name': employee_advance_name,
		'party_type': 'Employee',
		'party': employee,
		'is_advance': 'Yes'
	})

	je.append("accounts", {
		"account": return_account.account,
		"debit_in_account_currency": returning_amount,
		"account_currency": return_account.account_currency,
		"account_type": return_account.account_type,
		"exchange_rate": returning_exchange_rate
	})

	return je.as_dict()


