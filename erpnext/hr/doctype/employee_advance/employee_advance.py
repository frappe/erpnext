# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import erpnext
from frappe import _
from frappe.utils import flt, nowdate
from erpnext.controllers.status_updater import StatusUpdater
from six import string_types
import json

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
		self.db_set('status', 'Cancelled')

	def validate_employee_advance_account(self):
		company_currency = erpnext.get_company_currency(self.company)
		if (self.advance_account and
			company_currency != frappe.db.get_value('Account', self.advance_account, 'account_currency')):
			frappe.throw(_("Advance account currency should be same as company currency {0}")
				.format(company_currency))

	def set_payment_and_claimed_amount(self, update=False):
		payments = frappe.db.sql("""
			select ifnull(sum(debit), 0) as paid_amount, ifnull(sum(credit), 0) as returned_amount
			from `tabGL Entry`
			where ((against_voucher_type = 'Employee Advance' and against_voucher = %(name)s)
					or (original_against_voucher_type = 'Employee Advance' and original_against_voucher = %(name)s))
				and party_type = 'Employee'
				and party = %(party)s
				and voucher_type != 'Expense Claim'
		""", {"name": self.name, "party": self.employee}, as_dict=1)[0]

		salary_deduction = frappe.db.sql("""
			select sum(gle.credit-gle.debit)
			from `tabGL Entry` gle
			where gle.against_voucher_type = 'Employee Advance'
				and gle.against_voucher = %s
				and gle.party_type = 'Employee'
				and gle.party = %s
				and gle.voucher_type = 'Journal Entry'
				and exists(select ss.name from `tabSalary Slip` ss
					where ss.journal_entry = gle.voucher_no and ss.docstatus=1)
		""", (self.name, self.employee))
		salary_deduction = flt(salary_deduction[0][0]) if salary_deduction else 0

		payments.returned_amount -= salary_deduction

		claimed_amount = frappe.db.sql("""
			select ifnull(sum(credit), 0)
			from `tabGL Entry`
			where against_voucher_type = 'Employee Advance'
				and against_voucher = %s
				and party_type = 'Employee'
				and party = %s
				and voucher_type = 'Expense Claim'
		""", (self.name, self.employee))[0][0] or 0

		if flt(payments.paid_amount) > self.advance_amount:
			frappe.throw(_("Paid Amount cannot be greater than requested advance amount"), EmployeeAdvanceOverPayment)

		values = {
			"paid_amount": payments.paid_amount,
			"returned_amount": payments.returned_amount,
			"salary_deduction_amount": salary_deduction,
			"claimed_amount": flt(claimed_amount)
		}
		self.update(values)
		if update:
			self.db_set(values)

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
			balance_amount as advance_amount, purpose as remarks, project
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
def make_bank_entry(dt, dn, is_advance_return=False):
	from erpnext.accounts.doctype.journal_entry.journal_entry import get_default_bank_cash_account

	if not frappe.has_permission("Journal Entry", "write"):
		frappe.throw(_("Not Permitted"), frappe.PermissionError)

	doc = frappe.get_doc(dt, dn)
	payment_account = get_default_bank_cash_account(doc.company, account_type="Cash",
		mode_of_payment=doc.mode_of_payment)

	je = frappe.new_doc("Journal Entry")
	je.posting_date = nowdate()
	je.voucher_type = 'Bank Entry'
	je.company = doc.company
	je.cost_center = doc.cost_center
	je.project = doc.project
	je.remark = 'Payment against Employee Advance: ' + dn + '\n' + doc.purpose

	je.append("accounts", {
		"account": doc.advance_account,
		"debit_in_account_currency": flt(doc.advance_amount) if not is_advance_return else 0,
		"credit_in_account_currency": flt(doc.advance_amount) if is_advance_return else 0,
		"reference_type": "Employee Advance",
		"reference_name": doc.name,
		"party_type": "Employee",
		"party": doc.employee
	})

	je.append("accounts", {
		"account": payment_account.account,
		"credit_in_account_currency": flt(doc.advance_amount) if not is_advance_return else 0,
		"debit_in_account_currency": flt(doc.advance_amount) if is_advance_return else 0,
		"account_currency": payment_account.account_currency,
		"account_type": payment_account.account_type
	})

	return je.as_dict()


@frappe.whitelist()
def make_multiple_bank_entries(names):
	from erpnext.accounts.doctype.journal_entry.journal_entry import get_default_bank_cash_account

	if not frappe.has_permission("Journal Entry", "write"):
		frappe.throw(_("Not Permitted"), frappe.PermissionError)

	if isinstance(names, string_types):
		names = json.loads(names)

	je = frappe.new_doc("Journal Entry")
	je.posting_date = nowdate()
	je.voucher_type = 'Bank Entry'

	total_amount = 0
	company = None

	for name in names:
		ead = frappe.get_doc("Employee Advance", name)

		if ead.docstatus != 1 or flt(ead.paid_amount):
			continue

		if not company:
			company = ead.company
			je.company = company
		elif ead.company != company:
			continue

		je.append("accounts", {
			"account": ead.advance_account,
			"debit_in_account_currency": flt(ead.advance_amount),
			"reference_type": "Employee Advance",
			"reference_name": ead.name,
			"party_type": "Employee",
			"party": ead.employee,
			"cost_center": ead.cost_center,
			"project": ead.project
		})
		total_amount += flt(ead.advance_amount)

	if not total_amount:
		frappe.throw(_("No Payable Employee Advance selected"))

	payment_account = get_default_bank_cash_account(je.company, account_type="Cash")
	je.append("accounts", {
		"account": payment_account.account,
		"credit_in_account_currency": total_amount,
		"account_currency": payment_account.account_currency,
		"account_type": payment_account.account_type
	})

	return je.as_dict()
