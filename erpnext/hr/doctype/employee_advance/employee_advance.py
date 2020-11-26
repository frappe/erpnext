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
		paid_amount = frappe.db.sql("""
			select ifnull(sum(debit), 0) as paid_amount
			from `tabGL Entry`
			where against_voucher_type = 'Employee Advance'
				and against_voucher = %s
				and party_type = 'Employee'
				and party = %s
		""", (self.name, self.employee), as_dict=1)[0].paid_amount

		return_amount = frappe.db.sql("""
			select ifnull(sum(credit), 0) as return_amount
			from `tabGL Entry`
			where against_voucher_type = 'Employee Advance'
				and voucher_type != 'Expense Claim'
				and against_voucher = %s
				and party_type = 'Employee'
				and party = %s
		""", (self.name, self.employee), as_dict=1)[0].return_amount

		if paid_amount != 0:
			paid_amount = flt(paid_amount) / flt(self.exchange_rate)
		if return_amount != 0:
			return_amount = flt(return_amount) / flt(self.exchange_rate)

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
	employee_due_amount = frappe.get_all("Employee Advance", \
		filters = {"employee":employee, "docstatus":1, "posting_date":("<=", posting_date)}, \
		fields = ["advance_amount", "paid_amount"])
	return sum([(emp.advance_amount - emp.paid_amount) for emp in employee_due_amount])

@frappe.whitelist()
def make_bank_entry(dt, dn):
	doc = frappe.get_doc(dt, dn)
	payment_account = get_default_bank_cash_account(doc.company, account_type="Cash",
		mode_of_payment=doc.mode_of_payment)
	if not payment_account:
		frappe.throw(_("Please set a Default Cash Account in Company defaults"))

	advance_account_currency = frappe.db.get_value('Account', doc.advance_account, 'account_currency')

	advance_amount, advance_exchange_rate = get_advance_amount_advance_exchange_rate(advance_account_currency,doc )

	paying_amount, paying_exchange_rate = get_paying_amount_paying_exchange_rate(payment_account, doc)

	je = frappe.new_doc("Journal Entry")
	je.posting_date = nowdate()
	je.voucher_type = 'Bank Entry'
	je.company = doc.company
	je.remark = 'Payment against Employee Advance: ' + dn + '\n' + doc.purpose
	je.multi_currency = 1 if advance_account_currency != payment_account.account_currency else 0

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

def get_advance_amount_advance_exchange_rate(advance_account_currency, doc):
	if advance_account_currency != doc.currency:
		advance_amount = flt(doc.advance_amount) * flt(doc.exchange_rate)
		advance_exchange_rate = 1
	else:
		advance_amount = doc.advance_amount
		advance_exchange_rate = doc.exchange_rate

	return advance_amount, advance_exchange_rate

def get_paying_amount_paying_exchange_rate(payment_account, doc):
	if payment_account.account_currency != doc.currency:
		paying_amount = flt(doc.advance_amount) * flt(doc.exchange_rate)
		paying_exchange_rate = 1
	else:
		paying_amount = doc.advance_amount
		paying_exchange_rate = doc.exchange_rate

	return paying_amount, paying_exchange_rate

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
def make_return_entry(employee, company, employee_advance_name, return_amount,  advance_account, currency, exchange_rate, mode_of_payment=None):
	bank_cash_account = get_default_bank_cash_account(company, account_type='Cash', mode_of_payment = mode_of_payment)
	if not bank_cash_account:
		frappe.throw(_("Please set a Default Cash Account in Company defaults"))
	
	advance_account_currency = frappe.db.get_value('Account', advance_account, 'account_currency')
	
	je = frappe.new_doc('Journal Entry')
	je.posting_date = nowdate()
	je.voucher_type = get_voucher_type(mode_of_payment)
	je.company = company
	je.remark = 'Return against Employee Advance: ' + employee_advance_name
	je.multi_currency = 1 if advance_account_currency != bank_cash_account.account_currency else 0

	advance_account_amount = flt(return_amount) if advance_account_currency==currency \
		else flt(return_amount) * flt(exchange_rate)

	je.append('accounts', {
		'account': advance_account,
		'credit_in_account_currency': advance_account_amount,
		'account_currency': advance_account_currency,
		'exchange_rate': flt(exchange_rate) if advance_account_currency == currency else 1,
		'reference_type': 'Employee Advance',
		'reference_name': employee_advance_name,
		'party_type': 'Employee',
		'party': employee,
		'is_advance': 'Yes'
	})

	bank_amount = flt(return_amount) if bank_cash_account.account_currency==currency \
		else flt(return_amount) * flt(exchange_rate)

	je.append("accounts", {
		"account": bank_cash_account.account,
		"debit_in_account_currency": bank_amount,
		"account_currency": bank_cash_account.account_currency,
		"account_type": bank_cash_account.account_type,
		"exchange_rate": flt(exchange_rate) if bank_cash_account.account_currency == currency else 1
	})

	return je.as_dict()

def get_voucher_type(mode_of_payment=None):
	voucher_type = "Cash Entry"

	if mode_of_payment:
		mode_of_payment_type = frappe.get_cached_value('Mode of Payment', mode_of_payment, 'type')
		if mode_of_payment_type == "Bank":
			voucher_type = "Bank Entry"

	return voucher_type