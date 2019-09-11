# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate, getdate, now_datetime, get_datetime, flt, date_diff, get_last_day, cint, get_datetime
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.accounts.general_ledger import make_gl_entries
from calendar import monthrange

class LoanInterestAccural(AccountsController):
	def validate(self):
		if not self.loan:
			frappe.throw(_("Loan is mandatory"))

		if not self.posting_date:
			self.posting_date = nowdate()

		if not self.interest_amount:
			frappe.throw(_("Interest Amount is mandatory"))


	def on_submit(self):
		self.make_gl_entries()

	def on_cancel(self):
		self.make_gl_entries(cancel=1)

	def make_gl_entries(self, cancel=0, adv_adj=0):
		gle_map = []

		gle_map.append(
			self.get_gl_dict({
				"account": self.loan_account,
				"party_type": self.applicant_type,
				"party": self.applicant,
				"against": self.interest_income_account,
				"debit": self.interest_amount,
				"debit_in_account_currency": self.interest_amount,
				"against_voucher_type": "Loan",
				"against_voucher": self.loan,
				"remarks": "Against Loan:" + self.loan,
				"cost_center": erpnext.get_default_cost_center(self.company)
			})
		)

		gle_map.append(
			self.get_gl_dict({
				"account": self.interest_income_account,
				"party_type": self.applicant_type,
				"party": self.applicant,
				"against": self.loan_account,
				"credit": self.interest_amount,
				"credit_in_account_currency":  self.interest_amount,
				"against_voucher_type": "Loan",
				"against_voucher": self.loan,
				"remarks": "Against Loan:" + self.loan,
				"cost_center": erpnext.get_default_cost_center(self.company)
			})
		)

		if gle_map:
			make_gl_entries(gle_map, cancel=cancel, adv_adj=adv_adj)


def make_accural_interest_entry(posting_date=None):
	open_loans = frappe.get_all("Loan",
		fields=["name", "total_payment", "total_amount_paid", "loan_account", "interest_income_account", "is_term_loan",
			"disbursement_date", "applicant_type", "applicant", "rate_of_interest", "total_interest_payable", "repayment_start_date"],
		filters= {
			"status": "Disbursed",
			"docstatus": 1
		})

	curr_month = get_datetime(posting_date).month or now_datetime().month

	if curr_month == 1:
		prev_month = 12
		year = get_datetime(posting_date).year - 1 if posting_date else now_datetime().year - 1
	else:
		prev_month = curr_month - 1
		year = get_datetime(posting_date).year if posting_date else now_datetime().year

	precision = cint(frappe.db.get_default("currency_precision")) or 4
	no_of_days_in_previous_month = monthrange(year, prev_month)[1]

	for loan in open_loans:

		disbursement_date = get_datetime(loan.disbursement_date)
		if (disbursement_date.month == prev_month) and (disbursement_date.year == year):
			no_of_days_in_previous_month = date_diff(get_last_day(disbursement_date), disbursement_date) + 1

		pending_principal_amount = loan.total_payment - loan.total_interest_payable \
			- loan.total_amount_paid

		interest_per_day = (pending_principal_amount * loan.rate_of_interest) / (365 * 100)
		payable_interest = interest_per_day * no_of_days_in_previous_month

		loan_interest_accural = frappe.new_doc("Loan Interest Accural")
		loan_interest_accural.loan = loan.name
		loan_interest_accural.applicant_type = loan.applicant_type
		loan_interest_accural.applicant = loan.applicant
		loan_interest_accural.interest_income_account = loan.interest_income_account
		loan_interest_accural.loan_account = loan.loan_account
		loan_interest_accural.pending_principal_amount = pending_principal_amount
		loan_interest_accural.interest_amount = payable_interest
		loan_interest_accural.posting_date = posting_date or nowdate()

		loan_interest_accural.save()
		loan_interest_accural.submit()




