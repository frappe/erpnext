# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import erpnext
from erpnext.controllers.status_updater import StatusUpdater
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate

class EmployeeAdvanceOverPayment(frappe.ValidationError):
	pass

class EmployeeAdvance(StatusUpdater):
	def onload(self):
		self.get("__onload").make_payment_via_journal_entry = frappe.db.get_single_value('Accounts Settings',
			'make_payment_via_journal_entry')

	def validate(self):
		self.set_status()
		self.validate_employee_advance_account()
		if self.task and not self.project:
			self.project = frappe.db.get_value("Task", self.task, "project")

	def on_cancel(self):
		self.set_status()

	def validate_employee_advance_account(self):
		company_currency = erpnext.get_company_currency(self.company)
		if (self.advance_account and
			company_currency != frappe.db.get_value('Account', self.advance_account, 'account_currency')):
			frappe.throw(_("Advance account currency should be same as company currency {0}")
				.format(company_currency))

	def set_total_advance_paid(self):
		payments = frappe.db.sql("""
			select ifnull(sum(debit), 0) as paid_amount, ifnull(sum(credit), 0) as returned_amount
			from `tabGL Entry`
			where against_voucher_type = 'Employee Advance'
				and against_voucher = %s
				and party_type = 'Employee'
				and party = %s
				and voucher_type != 'Expense Claim'
		""", (self.name, self.employee), as_dict=1)[0]

		if flt(payments.paid_amount) > self.advance_amount:
			frappe.throw(_("Paid Amount cannot be greater than requested advance amount"), EmployeeAdvanceOverPayment)

		self.db_set("paid_amount", payments.paid_amount)
		self.db_set("returned_amount", payments.returned_amount)
		self.set_status(update=True)

	def update_claimed_amount(self):
		claimed_amount = frappe.db.sql("""
			select ifnull(sum(credit), 0)
			from `tabGL Entry`
			where against_voucher_type = 'Employee Advance'
				and against_voucher = %s
				and party_type = 'Employee'
				and party = %s
				and voucher_type = 'Expense Claim'
		""", (self.name, self.employee))[0][0] or 0

		self.db_set("claimed_amount", flt(claimed_amount))
		self.set_status(update=True)

@frappe.whitelist()
def get_due_advance_amount(employee, posting_date):
	employee_due_amount = frappe.get_all("Employee Advance", \
		filters = {"employee":employee, "docstatus":1, "posting_date":("<=", posting_date)}, \
		fields = ["advance_amount", "paid_amount"])
	return sum([(emp.advance_amount - emp.paid_amount) for emp in employee_due_amount])

@frappe.whitelist()
def get_unclaimed_advances(employee, advance_account):
	return frappe.db.sql("""
		select 'Employee Advance' as reference_type, name as reference_name, posting_date, paid_amount,
			balance_amount as advance_amount, purpose as remarks
		from `tabEmployee Advance`
		where docstatus=1 and employee=%s and advance_account=%s and balance_amount > 0
		order by posting_date
	""", [employee, advance_account], as_dict=1)

@frappe.whitelist()
def get_advance_details(employee_advance):
	details = frappe.db.sql("""
		select name as employee_advance, posting_date, advance_account, paid_amount as advance_paid,
			balance_amount as unclaimed_amount, balance_amount as allocated_amount
		from `tabEmployee Advance`
		where docstatus=1 and name=%s
	""", employee_advance, as_dict=1)
	return details[0] if details else {}

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
		"party": doc.employee
	})

	je.append("accounts", {
		"account": payment_account.account,
		"credit_in_account_currency": flt(doc.advance_amount),
		"account_currency": payment_account.account_currency,
		"account_type": payment_account.account_type
	})

	return je.as_dict()
