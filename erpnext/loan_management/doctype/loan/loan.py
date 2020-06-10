# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, math, json
import erpnext
from frappe import _
from frappe.utils import flt, rounded, add_months, nowdate, getdate, now_datetime

from erpnext.controllers.accounts_controller import AccountsController

class Loan(AccountsController):
	def validate(self):
		self.set_loan_amount()

		self.set_missing_fields()
		self.validate_accounts()
		self.validate_loan_security_pledge()
		self.validate_loan_amount()
		self.check_sanctioned_amount_limit()
		self.validate_repay_from_salary()

		if self.is_term_loan:
			validate_repayment_method(self.repayment_method, self.loan_amount, self.monthly_repayment_amount,
				self.repayment_periods, self.is_term_loan)
			self.make_repayment_schedule()
			self.set_repayment_period()

		self.calculate_totals()

	def validate_accounts(self):
		for fieldname in ['payment_account', 'loan_account', 'interest_income_account', 'penalty_income_account']:
			company = frappe.get_value("Account", self.get(fieldname), 'company')

			if company != self.company:
				frappe.throw(_("Account {0} does not belongs to company {1}").format(frappe.bold(self.get(fieldname)),
					frappe.bold(self.company)))

	def on_submit(self):
		self.link_loan_security_pledge()

	def on_cancel(self):
		self.unlink_loan_security_pledge()

	def set_missing_fields(self):
		if not self.company:
			self.company = erpnext.get_default_company()

		if not self.posting_date:
			self.posting_date = nowdate()

		if self.loan_type and not self.rate_of_interest:
			self.rate_of_interest = frappe.db.get_value("Loan Type", self.loan_type, "rate_of_interest")

		if self.repayment_method == "Repay Over Number of Periods":
			self.monthly_repayment_amount = get_monthly_repayment_amount(self.repayment_method, self.loan_amount, self.rate_of_interest, self.repayment_periods)

	def validate_loan_security_pledge(self):

		if self.is_secured_loan and not self.loan_security_pledge:
			frappe.throw(_("Loan Security Pledge is mandatory for secured loan"))

		if self.loan_security_pledge:
			loan_security_details = frappe.db.get_value("Loan Security Pledge", self.loan_security_pledge,
					['loan', 'company'], as_dict=1)

			if loan_security_details.loan:
				frappe.throw(_("Loan Security Pledge already pledged against loan {0}").format(loan_security_details.loan))

			if loan_security_details.company != self.company:
				frappe.throw(_("Loan Security Pledge Company and Loan Company must be same"))

	def check_sanctioned_amount_limit(self):
		total_loan_amount = get_total_loan_amount(self.applicant_type, self.applicant, self.company)
		sanctioned_amount_limit = get_sanctioned_amount_limit(self.applicant_type, self.applicant, self.company)

		if sanctioned_amount_limit and flt(self.loan_amount) + flt(total_loan_amount) > flt(sanctioned_amount_limit):
			frappe.throw(_("Sanctioned Amount limit crossed for {0} {1}").format(self.applicant_type, frappe.bold(self.applicant)))

	def validate_repay_from_salary(self):
		if not self.is_term_loan and self.repay_from_salary:
			frappe.throw(_("Repay From Salary can be selected only for term loans"))

	def make_repayment_schedule(self):

		if not self.repayment_start_date:
			frappe.throw(_("Repayment Start Date is mandatory for term loans"))

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

		if self.is_term_loan:
			for data in self.repayment_schedule:
				self.total_payment += data.total_payment
				self.total_interest_payable +=data.interest_amount
		else:
			self.total_payment = self.loan_amount

	def set_loan_amount(self):

		if not self.loan_amount and self.is_secured_loan and self.loan_security_pledge:
			self.loan_amount = self.maximum_loan_value

	def validate_loan_amount(self):
		if self.is_secured_loan and self.loan_amount > self.maximum_loan_value:
			msg = _("Loan amount cannot be greater than {0}").format(self.maximum_loan_value)
			frappe.throw(msg)

		if not self.loan_amount:
			frappe.throw(_("Loan amount is mandatory"))

	def link_loan_security_pledge(self):
		frappe.db.sql("""UPDATE `tabLoan Security Pledge` SET
			loan = %s, status = 'Pledged', pledge_time = %s
			where name = %s """, (self.name, now_datetime(), self.loan_security_pledge))

	def unlink_loan_security_pledge(self):
		frappe.db.sql("""UPDATE `tabLoan Security Pledge` SET
			loan = '', status = 'Unpledged'
			where name = %s """, (self.loan_security_pledge))

def update_total_amount_paid(doc):
	total_amount_paid = 0
	for data in doc.repayment_schedule:
		if data.paid:
			total_amount_paid += data.total_payment
	frappe.db.set_value("Loan", doc.name, "total_amount_paid", total_amount_paid)

def get_total_loan_amount(applicant_type, applicant, company):
	return frappe.db.get_value('Loan',
		{'applicant_type': applicant_type, 'company': company, 'applicant': applicant, 'docstatus': 1},
		'sum(loan_amount)')

def get_sanctioned_amount_limit(applicant_type, applicant, company):
	return frappe.db.get_value('Sanctioned Loan Amount',
		{'applicant_type': applicant_type, 'company': company, 'applicant': applicant},
		'sanctioned_amount_limit')

def validate_repayment_method(repayment_method, loan_amount, monthly_repayment_amount, repayment_periods, is_term_loan):

	if is_term_loan and not repayment_method:
		frappe.throw(_("Repayment Method is mandatory for term loans"))

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

def close_loan(loan, total_amount_paid):
	frappe.db.set_value("Loan", loan, "total_amount_paid", total_amount_paid)
	frappe.db.set_value("Loan", loan, "status", "Closed")

@frappe.whitelist()
def make_loan_disbursement(loan, company, applicant_type, applicant, pending_amount=0, as_dict=0):
	disbursement_entry = frappe.new_doc("Loan Disbursement")
	disbursement_entry.against_loan = loan
	disbursement_entry.applicant_type = applicant_type
	disbursement_entry.applicant = applicant
	disbursement_entry.company = company
	disbursement_entry.disbursement_date = nowdate()

	disbursement_entry.disbursed_amount = pending_amount
	if as_dict:
		return disbursement_entry.as_dict()
	else:
		return disbursement_entry

@frappe.whitelist()
def make_repayment_entry(loan, applicant_type, applicant, loan_type, company, as_dict=0):
	repayment_entry = frappe.new_doc("Loan Repayment")
	repayment_entry.against_loan = loan
	repayment_entry.applicant_type = applicant_type
	repayment_entry.applicant = applicant
	repayment_entry.company = company
	repayment_entry.loan_type = loan_type
	repayment_entry.posting_date = nowdate()

	if as_dict:
		return repayment_entry.as_dict()
	else:
		return repayment_entry

@frappe.whitelist()
def create_loan_security_unpledge(loan, applicant_type, applicant, company, as_dict=1):
	loan_security_pledge_details = frappe.db.sql("""
		SELECT p.parent, p.loan_security, p.qty as qty FROM `tabLoan Security Pledge` lsp , `tabPledge` p
		WHERE p.parent = lsp.name AND lsp.loan = %s AND lsp.docstatus = 1
	""",(loan), as_dict=1)

	unpledge_request = frappe.new_doc("Loan Security Unpledge")
	unpledge_request.applicant_type = applicant_type
	unpledge_request.applicant = applicant
	unpledge_request.loan = loan
	unpledge_request.company = company

	for loan_security in loan_security_pledge_details:
		unpledge_request.append('securities', {
			"loan_security": loan_security.loan_security,
			"qty": loan_security.qty
		})

	if as_dict:
		return unpledge_request.as_dict()
	else:
		return unpledge_request



