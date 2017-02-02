# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, math
import erpnext
from frappe import _
from frappe.utils import flt, rounded, add_months, nowdate
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.accounts.general_ledger import make_gl_entries

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

	def on_submit(self):
		self.make_gl_entries()

	def on_cancel(self):
		self.make_gl_entries()

	def make_gl_entries(self):
		gl_entries = []
		# Gl entries for employee loan account
		gl_entries.append(
			self.get_gl_dict({
				"account": self.employee_loan_account,
				"party_type": "Employee",
				"party": self.employee,
				"debit": self.loan_amount,
				"debit_in_account_currency": self.loan_amount
			})
		)
		# Gl entries for payment account
		gl_entries.append(
			self.get_gl_dict({
				"account": self.payment_account,
				"credit": self.loan_amount,
				"credit_in_account_currency": self.loan_amount
			})
		)
		make_gl_entries(gl_entries, cancel=(self.docstatus == 2))

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

	def update_status(self):
		if self.disbursement_date:
			self.status = "Loan Paid"
		if len(self.repayment_schedule)>0:
			self.status = "repayment in progress"
	
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
		return employee_loan