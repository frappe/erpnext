# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate

class EmployeeAdvanceOverPayment(frappe.ValidationError):
	pass

class EmployeeAdvance(Document):
	def onload(self):
		self.get("__onload").make_payment_via_journal_entry = frappe.db.get_single_value('Accounts Settings', 
			'make_payment_via_journal_entry')

	def validate(self):
		self.set_status()

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

	def set_total_advance_paid(self):
		paid_amount = frappe.db.sql("""
			select ifnull(sum(debit_in_account_currency), 0) as paid_amount
			from `tabGL Entry`
			where against_voucher_type = 'Employee Advance' 
				and against_voucher = %s
				and party_type = 'Employee'
				and party = %s
		""", (self.name, self.employee), as_dict=1)[0].paid_amount

		if flt(paid_amount) > self.advance_amount:
			frappe.throw(_("Row {0}# Paid Amount cannot be greater than requested advance amount"),
				EmployeeAdvanceOverPayment)

		self.db_set("paid_amount", paid_amount)
		self.set_status()
		frappe.db.set_value("Employee Advance", self.name , "status", self.status)

	def update_claimed_amount(self):
		claimed_amount = frappe.db.sql("""
			select sum(ifnull(allocated_amount, 0))
			from `tabExpense Claim Advance`
			where employee_advance = %s and docstatus=1 and allocated_amount > 0
		""", self.name)[0][0]

		if claimed_amount:
			frappe.db.set_value("Employee Advance", self.name, "claimed_amount", claimed_amount)

@frappe.whitelist()
def make_bank_entry(dt, dn):
	from erpnext.accounts.doctype.journal_entry.journal_entry import get_default_bank_cash_account

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