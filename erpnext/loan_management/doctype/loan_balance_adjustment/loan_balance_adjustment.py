# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import add_days, nowdate

import erpnext
from erpnext.accounts.general_ledger import make_gl_entries
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.loan_management.doctype.process_loan_interest_accrual.process_loan_interest_accrual import (
	process_loan_interest_accrual_for_demand_loans,
)


class LoanBalanceAdjustment(AccountsController):
	"""
	Add credit/debit adjustments to loan ledger.
	"""

	def validate(self):
		if self.amount == 0:
			frappe.throw(_("Amount cannot be zero"))
		if self.amount < 0:
			frappe.throw(_("Amount cannot be negative"))
		self.set_missing_values()

	def on_submit(self):
		self.set_status_and_amounts()
		self.make_gl_entries()

	def on_cancel(self):
		self.set_status_and_amounts(cancel=1)
		self.make_gl_entries(cancel=1)
		self.ignore_linked_doctypes = ["GL Entry", "Payment Ledger Entry"]

	def set_missing_values(self):
		if not self.posting_date:
			self.posting_date = nowdate()

		if not self.cost_center:
			self.cost_center = erpnext.get_default_cost_center(self.company)

	def set_status_and_amounts(self, cancel=0):
		loan_details = frappe.db.get_value(
			"Loan",
			self.loan,
			[
				"loan_amount",
				"credit_adjustment_amount",
				"debit_adjustment_amount",
				"total_payment",
				"total_principal_paid",
				"total_interest_payable",
				"status",
				"is_term_loan",
				"is_secured_loan",
			],
			as_dict=1,
		)

		if cancel:
			adjustment_amount = self.get_values_on_cancel(loan_details)
		else:
			adjustment_amount = self.get_values_on_submit(loan_details)

		if self.adjustment_type == "Credit Adjustment":
			adj_field = "credit_adjustment_amount"
		elif self.adjustment_type == "Debit Adjustment":
			adj_field = "debit_adjustment_amount"

		frappe.db.set_value("Loan", self.loan, {adj_field: adjustment_amount})

	def get_values_on_cancel(self, loan_details):
		if self.adjustment_type == "Credit Adjustment":
			adjustment_amount = loan_details.credit_adjustment_amount - self.amount
		elif self.adjustment_type == "Debit Adjustment":
			adjustment_amount = loan_details.debit_adjustment_amount - self.amount

		return adjustment_amount

	def get_values_on_submit(self, loan_details):
		if self.adjustment_type == "Credit Adjustment":
			adjustment_amount = loan_details.credit_adjustment_amount + self.amount
		elif self.adjustment_type == "Debit Adjustment":
			adjustment_amount = loan_details.debit_adjustment_amount + self.amount

		if loan_details.status in ("Disbursed", "Partially Disbursed") and not loan_details.is_term_loan:
			process_loan_interest_accrual_for_demand_loans(
				posting_date=add_days(self.posting_date, -1),
				loan=self.loan,
				accrual_type=self.adjustment_type,
			)

		return adjustment_amount

	def make_gl_entries(self, cancel=0, adv_adj=0):
		gle_map = []
		loan_account = frappe.db.get_value("Loan", self.loan, "loan_account")
		remarks = "{} against loan {}".format(self.adjustment_type.capitalize(), self.loan)
		if self.reference_number:
			remarks += " with reference no. {}".format(self.reference_number)

		loan_entry = {
			"account": loan_account,
			"against": self.adjustment_account,
			"against_voucher_type": "Loan",
			"against_voucher": self.loan,
			"remarks": _(remarks),
			"cost_center": self.cost_center,
			"party_type": self.applicant_type,
			"party": self.applicant,
			"posting_date": self.posting_date,
		}
		company_entry = {
			"account": self.adjustment_account,
			"against": loan_account,
			"against_voucher_type": "Loan",
			"against_voucher": self.loan,
			"remarks": _(remarks),
			"cost_center": self.cost_center,
			"posting_date": self.posting_date,
		}
		if self.adjustment_type == "Credit Adjustment":
			loan_entry["credit"] = self.amount
			loan_entry["credit_in_account_currency"] = self.amount

			company_entry["debit"] = self.amount
			company_entry["debit_in_account_currency"] = self.amount

		elif self.adjustment_type == "Debit Adjustment":
			loan_entry["debit"] = self.amount
			loan_entry["debit_in_account_currency"] = self.amount

			company_entry["credit"] = self.amount
			company_entry["credit_in_account_currency"] = self.amount

		gle_map.append(self.get_gl_dict(loan_entry))

		gle_map.append(self.get_gl_dict(company_entry))

		if gle_map:
			make_gl_entries(gle_map, cancel=cancel, adv_adj=adv_adj, merge_entries=False)
