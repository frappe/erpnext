# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, math
import erpnext
from frappe import _
from frappe.utils import flt, rounded, add_months, nowdate
from erpnext.controllers.accounts_controller import AccountsController

class EmployeeLoan(AccountsController):
	def validate(self):
		check_repayment_method(self.repayment_method, self.loan_amount, self.monthly_repayment_amount, self.repayment_periods)
		if not self.company:
			self.company = erpnext.get_default_company()
		if not self.posting_date:
			self.posting_date = nowdate()
		if self.loan_type and not self.rate_of_interest:
			self.rate_of_interest = frappe.db.get_value("Loan Type", self.loan_type, "rate_of_interest")
		if self.repayment_method == "Repay Over Number of Periods":
			self.monthly_repayment_amount = get_monthly_repayment_amount(self.repayment_method, self.loan_amount, self.rate_of_interest, self.repayment_periods)

		self.make_repayment_schedule()
		self.set_repayment_period()
		self.calculate_totals()

	def make_jv_entry(self):
		self.check_permission('write')
		journal_entry = frappe.new_doc('Journal Entry')
		journal_entry.voucher_type = 'Bank Entry'
		journal_entry.user_remark = _('Against Employee Loan: {0}').format(self.name)
		journal_entry.company = self.company
		journal_entry.posting_date = nowdate()

		account_amt_list = []

		account_amt_list.append({
			"account": self.employee_loan_account,
			"party_type": "Employee",
			"party": self.employee,
			"debit_in_account_currency": self.loan_amount,
			"reference_type": "Employee Loan",
			"reference_name": self.name,
			})
		account_amt_list.append({
			"account": self.payment_account,
			"credit_in_account_currency": self.loan_amount,
			"reference_type": "Employee Loan",
			"reference_name": self.name,
			})
		journal_entry.set("accounts", account_amt_list)
		return journal_entry.as_dict()

	def make_repayment_schedule(self):
		self.repayment_schedule = []
		payment_date = self.disbursement_date
		balance_amount = self.loan_amount

		while(balance_amount > 0):
			interest_amount = rounded(balance_amount * flt(self.rate_of_interest) / (12*100))
			principal_amount = self.monthly_repayment_amount - interest_amount
			balance_amount = rounded(balance_amount + interest_amount - self.monthly_repayment_amount)

			if balance_amount < 0:
				principal_amount += balance_amount
				balance_amount = 0.0

			total_payment = principal_amount + interest_amount

			self.append("repayment_schedule", {
				"payment_date": payment_date,
				"principal_amount": principal_amount,
				"interest_amount": interest_amount,
				"total_payment": total_payment,
				"balance_loan_amount": balance_amount
			})

			next_payment_date = add_months(payment_date, 1)
			payment_date = next_payment_date

	def set_repayment_period(self):
		if self.repayment_method == "Repay Fixed Amount per Period":
			repayment_periods = len(self.repayment_schedule)

			self.repayment_periods = repayment_periods

	def calculate_totals(self):
		self.total_payment = 0
		self.total_interest_payable = 0
		for data in self.repayment_schedule:
			self.total_payment += data.total_payment
			self.total_interest_payable +=data.interest_amount


def update_disbursement_status(doc):
	disbursement = frappe.db.sql("""select posting_date, ifnull(sum(debit_in_account_currency), 0) as disbursed_amount 
		from `tabGL Entry` where against_voucher_type = 'Employee Loan' and against_voucher = %s""", 
		(doc.name), as_dict=1)[0]
	if disbursement.disbursed_amount == doc.loan_amount:
		frappe.db.set_value("Employee Loan", doc.name , "status", "Fully Disbursed")
	if disbursement.disbursed_amount < doc.loan_amount and disbursement.disbursed_amount != 0:
		frappe.db.set_value("Employee Loan", doc.name , "status", "Partially Disbursed")
	if disbursement.disbursed_amount == 0:
		frappe.db.set_value("Employee Loan", doc.name , "status", "Sanctioned")
	if disbursement.disbursed_amount > doc.loan_amount:
		frappe.throw(_("Disbursed Amount cannot be greater than Loan Amount {0}").format(doc.loan_amount))
	if disbursement.disbursed_amount > 0:
		frappe.db.set_value("Employee Loan", doc.name , "disbursement_date", disbursement.posting_date)	
	
def check_repayment_method(repayment_method, loan_amount, monthly_repayment_amount, repayment_periods):
	if repayment_method == "Repay Over Number of Periods" and not repayment_periods:
		frappe.throw(_("Please enter Repayment Periods"))
		
	if repayment_method == "Repay Fixed Amount per Period":
		if not monthly_repayment_amount:
			frappe.throw(_("Please enter repayment Amount"))
		if monthly_repayment_amount > loan_amount:
			frappe.throw(_("Monthly Repayment Amount cannot be greater than Loan Amount"))

def get_monthly_repayment_amount(repayment_method, loan_amount, rate_of_interest, repayment_periods):
	if rate_of_interest:
		monthly_interest_rate = flt(rate_of_interest) / (12 *100)
		monthly_repayment_amount = math.ceil((loan_amount * monthly_interest_rate *
			(1 + monthly_interest_rate)**repayment_periods) \
			/ ((1 + monthly_interest_rate)**repayment_periods - 1))
	else:
		monthly_repayment_amount = math.ceil(flt(loan_amount) / repayment_periods)
	return monthly_repayment_amount

@frappe.whitelist()
def get_employee_loan_application(employee_loan_application):
	employee_loan = frappe.get_doc("Employee Loan Application", employee_loan_application)
	if employee_loan:
		return employee_loan.as_dict()

@frappe.whitelist()
def make_jv_entry(employee_loan, company, employee_loan_account, employee, loan_amount, payment_account=None):
	journal_entry = frappe.new_doc('Journal Entry')
	journal_entry.voucher_type = 'Bank Entry'
	journal_entry.user_remark = _('Against Employee Loan: {0}').format(employee_loan)
	journal_entry.company = company
	journal_entry.posting_date = nowdate()

	account_amt_list = []

	account_amt_list.append({
		"account": employee_loan_account,
		"debit_in_account_currency": loan_amount,
		"reference_type": "Employee Loan",
		"reference_name": employee_loan,
		})
	account_amt_list.append({
		"account": payment_account,
		"credit_in_account_currency": loan_amount,
		"reference_type": "Employee Loan",
		"reference_name": employee_loan,
		})
	journal_entry.set("accounts", account_amt_list)
	return journal_entry.as_dict()