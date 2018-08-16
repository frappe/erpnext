# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, math, json
import erpnext
from frappe import _
from frappe.utils import flt, rounded, add_months, nowdate
from erpnext.controllers.accounts_controller import AccountsController

class Loan(AccountsController):
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
		if self.status == "Repaid/Closed":
			self.total_amount_paid = self.total_payment
		if self.status == 'Disbursed' and self.repayment_start_date < self.disbursement_date:
			frappe.throw(_("Repayment Start Date cannot be before Disbursement Date."))

		if self.status == "Disbursed":
			self.make_repayment_schedule()
			self.set_repayment_period()
			self.calculate_totals()

	def make_jv_entry(self):
		self.check_permission('write')
		journal_entry = frappe.new_doc('Journal Entry')
		journal_entry.voucher_type = 'Bank Entry'
		journal_entry.user_remark = _('Against Loan: {0}').format(self.name)
		journal_entry.company = self.company
		journal_entry.posting_date = nowdate()

		account_amt_list = []

		account_amt_list.append({
			"account": self.loan_account,
			"party_type": self.applicant_type,
			"party": self.applicant,
			"debit_in_account_currency": self.loan_amount,
			"reference_type": "Loan",
			"reference_name": self.name,
			})
		account_amt_list.append({
			"account": self.payment_account,
			"credit_in_account_currency": self.loan_amount,
			"reference_type": "Loan",
			"reference_name": self.name,
			})
		journal_entry.set("accounts", account_amt_list)
		return journal_entry.as_dict()

	def make_repayment_schedule(self):
		self.repayment_schedule = []
		payment_date = self.repayment_start_date
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
		self.total_amount_paid = 0
		for data in self.repayment_schedule:
			self.total_payment += data.total_payment
			self.total_interest_payable +=data.interest_amount
			if data.paid:
				self.total_amount_paid += data.total_payment

def update_total_amount_paid(doc):
	total_amount_paid = 0
	for data in doc.repayment_schedule:
		if data.paid:
			total_amount_paid += data.total_payment
	frappe.db.set_value("Loan", doc.name, "total_amount_paid", total_amount_paid)

def update_disbursement_status(doc):
	disbursement = frappe.db.sql("""select posting_date, ifnull(sum(credit_in_account_currency), 0) as disbursed_amount
		from `tabGL Entry` where account = %s and against_voucher_type = 'Loan' and against_voucher = %s""",
		(doc.payment_account, doc.name), as_dict=1)[0]
	if disbursement.disbursed_amount == doc.loan_amount:
		frappe.db.set_value("Loan", doc.name , "status", "Disbursed")
	if disbursement.disbursed_amount == 0:
		frappe.db.set_value("Loan", doc.name , "status", "Sanctioned")
	if disbursement.disbursed_amount > doc.loan_amount:
		frappe.throw(_("Disbursed Amount cannot be greater than Loan Amount {0}").format(doc.loan_amount))
	if disbursement.disbursed_amount > 0:
		frappe.db.set_value("Loan", doc.name , "disbursement_date", disbursement.posting_date)
		frappe.db.set_value("Loan", doc.name , "repayment_start_date", disbursement.posting_date)

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
def get_loan_application(loan_application):
	loan = frappe.get_doc("Loan Application", loan_application)
	if loan:
		return loan.as_dict()

@frappe.whitelist()
def make_repayment_entry(payment_rows, loan, company, loan_account, applicant_type, applicant, \
	payment_account=None, interest_income_account=None):

	if isinstance(payment_rows, frappe.string_types):
		payment_rows_list = json.loads(payment_rows)
	else:
		frappe.throw(_("No repayments available for Journal Entry"))

	if payment_rows_list:
		row_name = list(set(d["name"] for d in payment_rows_list))
	else:
		frappe.throw(_("No repayments selected for Journal Entry"))
	total_payment = 0
	principal_amount = 0
	interest_amount = 0
	for d in payment_rows_list:
		total_payment += d["total_payment"]
		principal_amount += d["principal_amount"]
		interest_amount += d["interest_amount"]

	journal_entry = frappe.new_doc('Journal Entry')
	journal_entry.voucher_type = 'Bank Entry'
	journal_entry.user_remark = _('Against Loan: {0}').format(loan)
	journal_entry.company = company
	journal_entry.posting_date = nowdate()
	journal_entry.paid_loan = json.dumps(row_name)
	account_amt_list = []

	account_amt_list.append({
		"account": payment_account,
		"debit_in_account_currency": total_payment,
		"reference_type": "Loan",
		"reference_name": loan,
		})
	account_amt_list.append({
		"account": loan_account,
		"credit_in_account_currency": principal_amount,
		"party_type": applicant_type,
		"party": applicant,
		"reference_type": "Loan",
		"reference_name": loan,
		})
	account_amt_list.append({
		"account": interest_income_account,
		"credit_in_account_currency": interest_amount,
		"reference_type": "Loan",
		"reference_name": loan,
		})
	journal_entry.set("accounts", account_amt_list)

	return journal_entry.as_dict()

@frappe.whitelist()
def make_jv_entry(loan, company, loan_account, applicant_type, applicant, loan_amount,payment_account=None):

	journal_entry = frappe.new_doc('Journal Entry')
	journal_entry.voucher_type = 'Bank Entry'
	journal_entry.user_remark = _('Against Loan: {0}').format(loan)
	journal_entry.company = company
	journal_entry.posting_date = nowdate()
	account_amt_list = []

	account_amt_list.append({
		"account": loan_account,
		"debit_in_account_currency": loan_amount,
		"party_type": applicant_type,
		"party": applicant,
		"reference_type": "Loan",
		"reference_name": loan,
		})
	account_amt_list.append({
		"account": payment_account,
		"credit_in_account_currency": loan_amount,
		"reference_type": "Loan",
		"reference_name": loan,
		})
	journal_entry.set("accounts", account_amt_list)
	return journal_entry.as_dict()