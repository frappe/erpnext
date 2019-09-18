# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, math
from frappe import _
from frappe.utils import flt, rounded
from frappe.model.mapper import get_mapped_doc
from frappe.model.document import Document
from erpnext.loan_management.doctype.loan.loan import get_monthly_repayment_amount, validate_repayment_method

class LoanApplication(Document):
	def validate(self):

		validate_repayment_method(self.repayment_method, self.loan_amount, self.repayment_amount,
			self.repayment_periods, self.is_term_loan)
		self.set_loan_amount()
		self.set_pledge_amount()
		self.validate_loan_amount()
		self.get_repayment_details()

	def validate_loan_amount(self):
		maximum_loan_limit = frappe.db.get_value('Loan Type', self.loan_type, 'maximum_loan_amount')
		if maximum_loan_limit and self.loan_amount > maximum_loan_limit:
			frappe.throw(_("Loan Amount cannot exceed Maximum Loan Amount of {0}").format(maximum_loan_limit))

		if self.maximum_loan_amount and self.loan_amount > self.maximum_loan_amount:
			frappe.throw(_("Loan Amount exceeds maximum loan amount of {0} as per proposed securities").format(self.maximum_loan_amount))

	def set_pledge_amount(self):
		for proposed_pledge in self.proposed_pledges:
			proposed_pledge.amount = proposed_pledge.qty * proposed_pledge.loan_security_price

	def get_repayment_details(self):

		if self.is_term_loan:
			if self.repayment_method == "Repay Over Number of Periods":
				self.repayment_amount = get_monthly_repayment_amount(self.repayment_method, self.loan_amount, self.rate_of_interest, self.repayment_periods)

			if self.repayment_method == "Repay Fixed Amount per Period":
				monthly_interest_rate = flt(self.rate_of_interest) / (12 *100)
				if monthly_interest_rate:
					min_repayment_amount = self.loan_amount*monthly_interest_rate
					if self.repayment_amount - min_repayment_amount <= 0:
						frappe.throw(_("Repayment Amount must be greater than " \
							+ str(flt(min_repayment_amount, 2))))
					self.repayment_periods = math.ceil((math.log(self.repayment_amount) -
						math.log(self.repayment_amount - min_repayment_amount)) /(math.log(1 + monthly_interest_rate)))
				else:
					self.repayment_periods = self.loan_amount / self.repayment_amount

			self.calculate_payable_amount()
		else:
			self.total_payable_amount = self.loan_amount

	def calculate_payable_amount(self):
		balance_amount = self.loan_amount
		self.total_payable_amount = 0
		self.total_payable_interest = 0

		while(balance_amount > 0):
			interest_amount = rounded(balance_amount * flt(self.rate_of_interest) / (12*100))
			balance_amount = rounded(balance_amount + interest_amount - self.repayment_amount)

			self.total_payable_interest += interest_amount

		self.total_payable_amount = self.loan_amount + self.total_payable_interest

	def set_loan_amount(self):
		if not self.loan_amount and self.is_secured_loan and self.proposed_pledges:
			self.loan_amount = 0
			for security in self.loan_security_pledges:
				self.loan_amount += security.amount - (security.amount * security.haircut/100)

@frappe.whitelist()
def create_loan(source_name, target_doc = None):
	def update_accounts(source_doc, target_doc, source_parent):
		account_details = frappe.get_all("Loan Type",
		 fields=["mode_of_payment", "payment_account","loan_account", "interest_income_account", "penalty_income_account"],
		 filters = {'name': source_doc.loan_type}
		)[0]

		target_doc.mode_of_payment = account_details.mode_of_payment
		target_doc.payment_account = account_details.payment_account
		target_doc.loan_account = account_details.loan_account
		target_doc.interest_income_account = account_details.interest_income_account
		target_doc.penalty_income_account = account_details.penalty_income_account

	doclist = get_mapped_doc("Loan Application", source_name, {
		"Loan Application": {
			"doctype": "Loan",
			"validation": {
				"docstatus": ["=", 1]
			},
			"postprocess": update_accounts
		}
	}, target_doc)

	return doclist

@frappe.whitelist()
def create_pledge(loan_application):
	loan_application_doc = frappe.get_doc("Loan Application", loan_application)

	lsp = frappe.new_doc("Loan Security Pledge")
	lsp.applicant = loan_application_doc.applicant
	lsp.loan_application = loan_application_doc.name

	for pledge in loan_application_doc.proposed_pledges:

		lsp.append('loan_security_pledges', {
			"loan_security": pledge.loan_security,
			"qty": pledge.qty,
			"loan_security_price": pledge.loan_security_price,
			"haircut": pledge.haircut
		})

	lsp.save()
	lsp.submit()

	message = _("Loan Security Pledge Created : {0}").format(lsp.name)
	frappe.msgprint(message)