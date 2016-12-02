# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, math
from frappe.utils import flt, rounded, cint, add_months, date_diff
from frappe.model.document import Document

class EmployeeLoan(Document):
	def validate(self):
		self.set_emi_amount()
		self.make_amortization_schedule()
		self.set_repayment_period()
		self.calculate_totals()

	def set_emi_amount(self):
		if self.repayment_method == "Repay Over Number of Periods":
			if self.rate_of_interest:
				monthly_interest_rate = flt(self.rate_of_interest) / (12 *100)
				self.emi_amount = math.ceil((self.loan_amount * monthly_interest_rate * (1 + monthly_interest_rate)**self.repayment_periods) \
					/((1 + monthly_interest_rate)**self.repayment_periods - 1))
			else:
				self.emi_amount = math.ceil(flt(self.loan_amount) / self.repayment_periods)

	def make_amortization_schedule(self):
		self.amortization_schedule = []
		payment_date = self.emi_start_date
		interest_on_days = date_diff(self.emi_start_date, self.disbursement_date)

		balance_amount = self.loan_amount

		daily_interest_rate = flt(self.rate_of_interest) / (365 *100)		

		while(balance_amount > 0):
			interest_amount = math.ceil(balance_amount * flt(daily_interest_rate) * interest_on_days)
			principal_amount = self.emi_amount - interest_amount
			balance_amount = math.ceil(balance_amount + interest_amount - self.emi_amount)			

			if balance_amount < 0:
				principal_amount += balance_amount
				balance_amount = 0.0

			total_payment = principal_amount + interest_amount

			self.append("amortization_schedule", {
				"payment_date": payment_date,
				"principal_amount": principal_amount,
				"interest_amount": interest_amount,
				"total_payment": total_payment,
				"balance_loan_amount": balance_amount
			})

			next_payment_date = add_months(payment_date, 1)
			interest_on_days = date_diff(next_payment_date, payment_date)
			payment_date = next_payment_date

	def set_repayment_period(self):
		if self.repayment_method == "Repay Fixed Amount per Period":
			repayment_periods = len(self.amortization_schedule)

			self.repayment_periods = repayment_periods

	def calculate_totals(self):
		for data in self.amortization_schedule:
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