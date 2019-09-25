# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, erpnext
import json
from frappe import _
from frappe.utils import flt
from frappe.model.document import Document
from frappe.utils import date_diff, add_days, getdate, add_months, get_first_day
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.accounts.general_ledger import make_gl_entries

class LoanRepayment(AccountsController):

	def validate(self):
		amounts = calculate_amounts(self.against_loan, self.posting_date, self.loan_type, self.payment_type)
		self.set_missing_values(amounts)

	def before_submit(self):
		self.mark_as_paid()

	def on_submit(self):
		self.make_gl_entries()

	def on_cancel(self):
		self.mark_as_unpaid()
		self.make_gl_entries(cancel=1)

	def set_missing_values(self, amounts):
		if not self.posting_date:
			self.posting_date = nowdate()

		if not self.cost_center:
			self.cost_center = erpnext.get_default_cost_center(self.company)

		if not self.interest_payable:
			self.interest_payable = amounts['interest_amount']

		if not self.penalty_amount:
			self.penalty_amount = amounts['penalty_amount']

		if not self.pending_principal_amount:
			self.pending_principal_amount = amounts['pending_principal_amount']

		if not self.payable_principal_amount and self.is_term_loan:
			self.payable_principal_amount = amounts['payable_principal_amount']

		if not self.payable_amount:
			self.payable_amount = amounts['payable_amount']

		if amounts.get("paid_accrual_entries"):
			self.paid_accrual_entries = frappe.as_json(amounts.get("paid_accrual_entries"))


	def mark_as_paid(self):
		paid_payments = []
		paid_amount = self.amount_paid

		if not paid_amount:
			frappe.throw(_("Amount paid cannot be zero"))

		loan = frappe.get_doc("Loan", self.against_loan)

		principal_amount_paid = flt(self.amount_paid - self.penalty_amount - self.interest_payable, 2)
		paid_accrual_entries = json.loads(self.paid_accrual_entries)

		if principal_amount_paid < 0:
			msg = _("Paid amount cannot be less than {0}").format(self.penalty_amount + self.interest_payable)
			frappe.throw(msg)

		if self.is_term_loan and principal_amount_paid < flt(self.payable_principal_amount, 2):
			frappe.throw(_("Paid amount cannot be less than {0}".format(self.penalty_amount + self.interest_payable
				+ self.payable_principal_amount)))

		if self.payment_type == "Loan Closure" and principal_amount_paid < flt(self.pending_principal_amount, 2):
			msg = _("Amount of {0} is required for Loan closure").format(self.pending_principal_amount)

		frappe.db.sql("""UPDATE `tabLoan Interest Accrual`
			SET is_paid = 1 where name in (%s)""" #nosec
			% ", ".join(['%s']*len(paid_accrual_entries)), tuple(paid_accrual_entries))

		frappe.db.set_value("Loan", self.against_loan, "total_amount_paid", loan.total_amount_paid + principal_amount_paid)
		frappe.db.set_value("Loan", self.against_loan, "total_principal_paid", loan.total_principal_paid + principal_amount_paid)

		if loan.total_principal_paid + principal_amount_paid == loan.total_payment:
			frappe.db.set_value("Loan", self.against_loan, "status", "Loan Closure Requested")

	def mark_as_unpaid(self):

		loan = frappe.get_doc("Loan", self.against_loan)
		paid_accrual_entries = json.loads(self.paid_accrual_entries)

		principal_amount_paid = self.amount_paid - self.penalty_amount - self.interest_payable

		frappe.db.sql("""UPDATE `tabLoan Interest Accrual`
			SET is_paid = 1 where name in (%s)""" #nosec
			% ", ".join(['%s']*len(paid_accrual_entries)), tuple(paid_accrual_entries))

		frappe.db.set_value("Loan", self.against_loan, "total_amount_paid", loan.total_amount_paid - principal_amount_paid)
		frappe.db.set_value("Loan", self.against_loan, "total_principal_paid", loan.total_principal_paid - principal_amount_paid)

		if loan.status == "Closed":
			frappe.db.set_value("Loan", self.against_loan, "status", "Disbursed")

	def make_gl_entries(self, cancel=0, adv_adj=0):
		gle_map = []
		loan_details = frappe.get_doc("Loan", self.against_loan)

		gle_map.append(
			self.get_gl_dict({
				"account": loan_details.loan_account,
				"against": loan_details.payment_account,
				"debit": self.penalty_amount,
				"debit_in_account_currency": self.penalty_amount,
				"against_voucher_type": "Loan",
				"against_voucher": self.against_loan,
				"remarks": "Against Loan:" + self.against_loan,
				"cost_center": self.cost_center
			})
		)

		gle_map.append(
			self.get_gl_dict({
				"account": loan_details.penalty_income_account,
				"against": loan_details.payment_account,
				"credit": self.penalty_amount,
				"credit_in_account_currency": self.penalty_amount,
				"against_voucher_type": "Loan",
				"against_voucher": self.against_loan,
				"remarks": "Against Loan:" + self.against_loan,
				"cost_center": self.cost_center
			})
		)

		gle_map.append(
			self.get_gl_dict({
				"account": loan_details.payment_account,
				"against": loan_details.loan_account + ", " + loan_details.interest_income_account
						+ ", " + loan_details.penalty_income_account,
				"debit": self.amount_paid,
				"debit_in_account_currency": self.amount_paid ,
				"against_voucher_type": "Loan",
				"against_voucher": self.against_loan,
				"remarks": "Against Loan:" + self.against_loan,
				"cost_center": self.cost_center
			})
		)

		gle_map.append(
			self.get_gl_dict({
				"account": loan_details.loan_account,
				"party_type": loan_details.applicant_type,
				"party": loan_details.applicant,
				"against": loan_details.payment_account,
				"credit": self.amount_paid,
				"credit_in_account_currency": self.amount_paid,
				"against_voucher_type": "Loan",
				"against_voucher": self.against_loan,
				"remarks": "Against Loan:" + self.against_loan,
				"cost_center": self.cost_center
			})
		)

		if gle_map:
			make_gl_entries(gle_map, cancel=cancel, adv_adj=adv_adj)

def create_repayment_entry(loan, applicant, company, posting_date, loan_type,
	payment_type, interest_payable, payable_principal_amount, amount_paid, penalty_amount=None):

	lr = frappe.get_doc({
		"doctype": "Loan Repayment",
		"against_loan": loan,
		"payment_type": payment_type,
		"company": company,
		"posting_date": posting_date,
		"applicant": applicant,
		"penalty_amount": penalty_amount,
		"interets_payable": interest_payable,
		"payable_principal_amount": payable_principal_amount,
		"amount_paid": amount_paid,
		"loan_type": loan_type
	}).insert()

	return lr

def get_accured_interest_entries(against_loan):
	accured_interest_entries = frappe.get_all("Loan Interest Accrual",
		fields=["name", "interest_amount", "posting_date", "payable_principal_amount"],
		filters = {
			"loan": against_loan,
			"is_paid": 0
		})

	return accured_interest_entries

# This function returns the amounts that are payable at the time of loan repayment based on posting date
# So it pulls all the unpaid Loan Interest Accrual Entries and calculates the penalty if applicable

def get_amounts(amounts, against_loan, loan_type, posting_date):

	against_loan_doc = frappe.get_doc("Loan", against_loan)
	loan_type_details = frappe.get_doc("Loan Type", loan_type)
	accured_interest_entries = get_accured_interest_entries(against_loan_doc.name)

	paid_accrual_entries = []

	total_pending_interest = 0
	penalty_amount = 0
	payable_principal_amount = 0

	for entry in accured_interest_entries:
		# Loan repayment due date is one day after the loan interest is accrued
		# no of late days are calculated based on loan repayment posting date
		# and if no_of_late days are positive then penalty is levied

		due_date = add_days(entry.posting_date, 1)
		no_of_late_days = date_diff(posting_date,
					add_days(due_date, loan_type_details.grace_period_in_days)) + 1

		if no_of_late_days > 0 and (not against_loan_doc.repay_from_salary):
			penalty_amount += (entry.interest_amount * (loan_type_details.penalty_interest_rate / 100) * no_of_late_days)/365

		total_pending_interest += entry.interest_amount
		payable_principal_amount += entry.payable_principal_amount

		paid_accrual_entries.append(entry.name)

	pending_principal_amount = against_loan_doc.total_payment - against_loan_doc.total_principal_paid - against_loan_doc.total_interest_payable

	amounts["pending_principal_amount"] = pending_principal_amount
	amounts["payable_principal_amount"] = payable_principal_amount
	amounts["interest_amount"] = total_pending_interest
	amounts["penalty_amount"] = penalty_amount
	amounts["payable_amount"] = payable_principal_amount + total_pending_interest + penalty_amount

	amounts["paid_accrual_entries"] = paid_accrual_entries
	return amounts

@frappe.whitelist()
def calculate_amounts(against_loan, posting_date, loan_type, payment_type):

	amounts = {
		'penalty_amount': 0.0,
		'interest_amount': 0.0,
		'pending_principal_amount': 0.0,
		'payable_principal_amount': 0.0,
		'payable_amount': 0.0
	}

	amounts = get_amounts(amounts, against_loan, loan_type, posting_date)

	return amounts



