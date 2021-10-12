# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import add_days, flt, get_datetime, nowdate

import erpnext
from erpnext.accounts.general_ledger import make_gl_entries
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.loan_management.doctype.loan_security_unpledge.loan_security_unpledge import (
	get_pledged_security_qty,
)
from erpnext.loan_management.doctype.process_loan_interest_accrual.process_loan_interest_accrual import (
	process_loan_interest_accrual_for_demand_loans,
)


class LoanDisbursement(AccountsController):

	def validate(self):
		self.set_missing_values()
		self.validate_disbursal_amount()

	def on_submit(self):
		self.set_status_and_amounts()
		self.make_gl_entries()

	def on_cancel(self):
		self.set_status_and_amounts(cancel=1)
		self.make_gl_entries(cancel=1)
		self.ignore_linked_doctypes = ['GL Entry']

	def set_missing_values(self):
		if not self.disbursement_date:
			self.disbursement_date = nowdate()

		if not self.cost_center:
			self.cost_center = erpnext.get_default_cost_center(self.company)

		if not self.posting_date:
			self.posting_date = self.disbursement_date or nowdate()

		if not self.bank_account and self.applicant_type == "Customer":
			self.bank_account = frappe.db.get_value("Customer", self.applicant, "default_bank_account")

	def validate_disbursal_amount(self):
		possible_disbursal_amount = get_disbursal_amount(self.against_loan)

		if self.disbursed_amount > possible_disbursal_amount:
			frappe.throw(_("Disbursed Amount cannot be greater than {0}").format(possible_disbursal_amount))

	def set_status_and_amounts(self, cancel=0):
		loan_details = frappe.get_all("Loan",
			fields = ["loan_amount", "disbursed_amount", "total_payment", "total_principal_paid", "total_interest_payable",
				"status", "is_term_loan", "is_secured_loan"], filters= { "name": self.against_loan })[0]

		if cancel:
			disbursed_amount, status, total_payment = self.get_values_on_cancel(loan_details)
		else:
			disbursed_amount, status, total_payment = self.get_values_on_submit(loan_details)

		frappe.db.set_value("Loan", self.against_loan, {
			"disbursement_date": self.disbursement_date,
			"disbursed_amount": disbursed_amount,
			"status": status,
			"total_payment": total_payment
		})

	def get_values_on_cancel(self, loan_details):
		disbursed_amount = loan_details.disbursed_amount - self.disbursed_amount
		total_payment = loan_details.total_payment

		if loan_details.disbursed_amount > loan_details.loan_amount:
			topup_amount = loan_details.disbursed_amount - loan_details.loan_amount
			if topup_amount > self.disbursed_amount:
				topup_amount = self.disbursed_amount

			total_payment = total_payment - topup_amount

		if disbursed_amount == 0:
			status = "Sanctioned"

		elif disbursed_amount >= loan_details.loan_amount:
			status = "Disbursed"
		else:
			status = "Partially Disbursed"

		return disbursed_amount, status, total_payment

	def get_values_on_submit(self, loan_details):
		disbursed_amount = self.disbursed_amount + loan_details.disbursed_amount
		total_payment = loan_details.total_payment

		if loan_details.status in ("Disbursed", "Partially Disbursed") and not loan_details.is_term_loan:
			process_loan_interest_accrual_for_demand_loans(posting_date=add_days(self.disbursement_date, -1),
				loan=self.against_loan, accrual_type="Disbursement")

		if disbursed_amount > loan_details.loan_amount:
			topup_amount = disbursed_amount - loan_details.loan_amount

			if topup_amount < 0:
				topup_amount = 0

			if topup_amount > self.disbursed_amount:
				topup_amount = self.disbursed_amount

			total_payment = total_payment + topup_amount

		if flt(disbursed_amount) >= loan_details.loan_amount:
			status = "Disbursed"
		else:
			status = "Partially Disbursed"

		return disbursed_amount, status, total_payment

	def make_gl_entries(self, cancel=0, adv_adj=0):
		gle_map = []
		loan_details = frappe.get_doc("Loan", self.against_loan)

		gle_map.append(
			self.get_gl_dict({
				"account": loan_details.loan_account,
				"against": loan_details.payment_account,
				"debit": self.disbursed_amount,
				"debit_in_account_currency": self.disbursed_amount,
				"against_voucher_type": "Loan",
				"against_voucher": self.against_loan,
				"remarks": _("Disbursement against loan:") + self.against_loan,
				"cost_center": self.cost_center,
				"party_type": self.applicant_type,
				"party": self.applicant,
				"posting_date": self.disbursement_date
			})
		)

		gle_map.append(
			self.get_gl_dict({
				"account": loan_details.payment_account,
				"against": loan_details.loan_account,
				"credit": self.disbursed_amount,
				"credit_in_account_currency": self.disbursed_amount,
				"against_voucher_type": "Loan",
				"against_voucher": self.against_loan,
				"remarks": _("Disbursement against loan:") + self.against_loan,
				"cost_center": self.cost_center,
				"posting_date": self.disbursement_date
			})
		)

		if gle_map:
			make_gl_entries(gle_map, cancel=cancel, adv_adj=adv_adj)

def get_total_pledged_security_value(loan):
	update_time = get_datetime()

	loan_security_price_map = frappe._dict(frappe.get_all("Loan Security Price",
		fields=["loan_security", "loan_security_price"],
		filters = {
			"valid_from": ("<=", update_time),
			"valid_upto": (">=", update_time)
		}, as_list=1))

	hair_cut_map = frappe._dict(frappe.get_all('Loan Security',
		fields=["name", "haircut"], as_list=1))

	security_value = 0.0
	pledged_securities = get_pledged_security_qty(loan)

	for security, qty in pledged_securities.items():
		after_haircut_percentage = 100 - hair_cut_map.get(security)
		security_value += (loan_security_price_map.get(security) * qty * after_haircut_percentage)/100

	return security_value

@frappe.whitelist()
def get_disbursal_amount(loan, on_current_security_price=0):
	loan_details = frappe.get_value("Loan", loan, ["loan_amount", "disbursed_amount", "total_payment",
		"total_principal_paid", "total_interest_payable", "status", "is_term_loan", "is_secured_loan",
		"maximum_loan_amount"], as_dict=1)

	if loan_details.is_secured_loan and frappe.get_all('Loan Security Shortfall', filters={'loan': loan,
		'status': 'Pending'}):
		return 0

	if loan_details.status == 'Disbursed':
		pending_principal_amount = flt(loan_details.total_payment) - flt(loan_details.total_interest_payable) \
			- flt(loan_details.total_principal_paid)
	else:
		pending_principal_amount = flt(loan_details.disbursed_amount) - flt(loan_details.total_interest_payable) \
			- flt(loan_details.total_principal_paid)

	security_value = 0.0
	if loan_details.is_secured_loan and on_current_security_price:
		security_value = get_total_pledged_security_value(loan)

	if loan_details.is_secured_loan and not on_current_security_price:
		security_value = get_maximum_amount_as_per_pledged_security(loan)

	if not security_value and not loan_details.is_secured_loan:
		security_value = flt(loan_details.loan_amount)

	disbursal_amount = flt(security_value) - flt(pending_principal_amount)

	if loan_details.is_term_loan and (disbursal_amount + loan_details.loan_amount) > loan_details.loan_amount:
		disbursal_amount = loan_details.loan_amount - loan_details.disbursed_amount

	return disbursal_amount

def get_maximum_amount_as_per_pledged_security(loan):
	return flt(frappe.db.get_value('Loan Security Pledge', {'loan': loan}, 'sum(maximum_loan_value)'))
