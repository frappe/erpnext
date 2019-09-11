# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe.model.document import Document
from frappe.utils import nowdate, getdate
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.accounts.general_ledger import make_gl_entries

class LoanDisbursement(AccountsController):

	def validate(self):
		self.set_missing_values()

	def on_submit(self):
		self.set_status()
		self.make_gl_entries()

	def on_cancel(self):
		self.make_gl_entries(cancel=1)

	def set_missing_values(self):
		if not self.disbursement_date:
			self.disbursement_date = nowdate()

		if not self.cost_center:
			self.cost_center = erpnext.get_default_cost_center(self.company)

		if not self.posting_date:
			self.posting_date = self.disbursement_date or nowdate()

	def set_status(self):

		loan_details = frappe.get_all("Loan",
			fields = ["loan_amount", "disbursed_amount"],
			filters= { "name": self.against_loan }
		)[0]

		disbursed_amount = self.disbursed_amount + loan_details.disbursed_amount

		if disbursed_amount > loan_details.loan_amount:
			frappe.throw("Disbursed Amount cannot be greater than loan amount")

		if loan_details.loan_amount == disbursed_amount:
			frappe.db.set_value("Loan", self.against_loan, "status", "Disbursed")
		else:
			frappe.db.set_value("Loan", self.against_loan, "status", "Partially Disbursed")

		frappe.db.set_value("Loan", self.against_loan, "disbursement_date", self.disbursement_date)
		frappe.db.set_value("Loan", self.against_loan, "disbursed_amount", disbursed_amount)

	def make_gl_entries(self, cancel=0, adv_adj=0):
		gle_map = []
		loan_details = frappe.get_doc("Loan", self.against_loan)

		gle_map.append(
			self.get_gl_dict({
				"account": loan_details.loan_account,
				"against": loan_details.applicant,
				"debit": self.disbursed_amount,
				"debit_in_account_currency": self.disbursed_amount,
				"against_voucher_type": "Loan",
				"against_voucher": self.against_loan,
				"remarks": "Against Loan:" + self.against_loan,
				"cost_center": self.cost_center
			})
		)

		gle_map.append(
			self.get_gl_dict({
				"account": loan_details.payment_account,
				"against": loan_details.applicant,
				"credit": self.disbursed_amount,
				"credit_in_account_currency": self.disbursed_amount,
				"against_voucher_type": "Loan",
				"against_voucher": self.against_loan,
				"remarks": "Against Loan:" + self.against_loan,
				"cost_center": self.cost_center
			})
		)

		if gle_map:
			make_gl_entries(gle_map, cancel=cancel, adv_adj=adv_adj)
