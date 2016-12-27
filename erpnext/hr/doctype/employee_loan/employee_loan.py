# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, math
from frappe import _
from frappe.utils import flt, rounded, cint, add_months, date_diff
from frappe.model.document import Document

class EmployeeLoan(Document):
	def validate(self):
		check_repayment_method(self.repayment_method, self.loan_amount, self.emi_amount, self.repayment_periods)
		if self.repayment_method == "Repay Over Number of Periods":
			self.emi_amount = get_emi_amount(self.repayment_method, self.loan_amount, self.rate_of_interest, self.repayment_periods)
		self.make_emi_schedule()
		self.set_repayment_period()
		self.calculate_totals()

	def make_emi_schedule(self):
		self.emi_schedule = []
		payment_date = self.disbursement_date
		balance_amount = self.loan_amount

		while(balance_amount > 0):
			interest_amount = rounded(balance_amount * flt(self.rate_of_interest) / (12*100))
			principal_amount = self.emi_amount - interest_amount
			balance_amount = rounded(balance_amount + interest_amount - self.emi_amount)

			if balance_amount < 0:
				principal_amount += balance_amount
				balance_amount = 0.0

			total_payment = principal_amount + interest_amount

			self.append("emi_schedule", {
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
			repayment_periods = len(self.emi_schedule)

			self.repayment_periods = repayment_periods

	def calculate_totals(self):
		self.total_payment = 0
		self.total_interest_payable = 0
		for data in self.emi_schedule:
			self.total_payment += data.total_payment
			self.total_interest_payable +=data.interest_amount

	def get_employee_loan_application(self):
		employee_loan = frappe.get_doc("Employee Loan Application", self.employee_loan_application)
		if employee_loan:
			self.loan_type = employee_loan.loan_type
			self.loan_amount = employee_loan.loan_amount
			self.repayment_method = employee_loan.repayment_method
			self.emi_amount = employee_loan.emi_amount
			self.repayment_periods = employee_loan.repayment_periods
			self.rate_of_interest = frappe.db.get_value("Loan Type", self.loan_type, "rate_of_interest")

	def update_status(self):
		if self.disbursement_date:
			self.status = "Loan Paid"
		if len(self.emi_schedule)>0:
			self.status = "EMI in progress"

	
def check_repayment_method(repayment_method, loan_amount, emi_amount, repayment_periods):
	if repayment_method == "Repay Over Number of Periods" and not repayment_periods:
		frappe.throw(_("Please enter Repayment Periods"))
		
	if repayment_method == "Repay Fixed Amount per Period":
		if not emi_amount:
			frappe.throw(_("Please enter EMI Amount"))
		if emi_amount > loan_amount:
			frappe.throw(_("EMI Amount cannot be greater than Loan Amount"))

def get_emi_amount(repayment_method, loan_amount, rate_of_interest, repayment_periods):
	if repayment_method == "Repay Over Number of Periods":
		if rate_of_interest:
			monthly_interest_rate = flt(rate_of_interest) / (12 *100)
			emi_amount = math.ceil((loan_amount * monthly_interest_rate *
				(1 + monthly_interest_rate)**repayment_periods) \
				/ ((1 + monthly_interest_rate)**repayment_periods - 1))
	else:
		emi_amount = math.ceil(flt(loan_amount) / repayment_periods)
	return emi_amount