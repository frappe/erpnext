# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import cint, flt, getdate

import erpnext
from erpnext.accounts.general_ledger import make_gl_entries
from erpnext.controllers.accounts_controller import AccountsController


class LoanWriteOff(AccountsController):
	def validate(self):
		self.set_missing_values()
		self.validate_write_off_amount()

	def set_missing_values(self):
		if not self.cost_center:
			self.cost_center = erpnext.get_default_cost_center(self.company)

	def validate_write_off_amount(self):
		precision = cint(frappe.db.get_default("currency_precision")) or 2
		total_payment, principal_paid, interest_payable, written_off_amount = frappe.get_value(
			"Loan",
			self.loan,
			["total_payment", "total_principal_paid", "total_interest_payable", "written_off_amount"],
		)

		pending_principal_amount = flt(
			flt(total_payment) - flt(interest_payable) - flt(principal_paid) - flt(written_off_amount),
			precision,
		)

		if self.write_off_amount > pending_principal_amount:
			frappe.throw(_("Write off amount cannot be greater than pending principal amount"))

	def on_submit(self):
		self.update_outstanding_amount()
		self.make_gl_entries()

	def on_cancel(self):
		self.update_outstanding_amount(cancel=1)
		self.ignore_linked_doctypes = ["GL Entry", "Payment Ledger Entry"]
		self.make_gl_entries(cancel=1)

	def update_outstanding_amount(self, cancel=0):
		written_off_amount = frappe.db.get_value("Loan", self.loan, "written_off_amount")

		if cancel:
			written_off_amount -= self.write_off_amount
		else:
			written_off_amount += self.write_off_amount

		frappe.db.set_value("Loan", self.loan, "written_off_amount", written_off_amount)

	def make_gl_entries(self, cancel=0):
		gl_entries = []
		loan_details = frappe.get_doc("Loan", self.loan)

		gl_entries.append(
			self.get_gl_dict(
				{
					"account": self.write_off_account,
					"against": loan_details.loan_account,
					"debit": self.write_off_amount,
					"debit_in_account_currency": self.write_off_amount,
					"against_voucher_type": "Loan",
					"against_voucher": self.loan,
					"remarks": _("Against Loan:") + self.loan,
					"cost_center": self.cost_center,
					"posting_date": getdate(self.posting_date),
				}
			)
		)

		gl_entries.append(
			self.get_gl_dict(
				{
					"account": loan_details.loan_account,
					"party_type": loan_details.applicant_type,
					"party": loan_details.applicant,
					"against": self.write_off_account,
					"credit": self.write_off_amount,
					"credit_in_account_currency": self.write_off_amount,
					"against_voucher_type": "Loan",
					"against_voucher": self.loan,
					"remarks": _("Against Loan:") + self.loan,
					"cost_center": self.cost_center,
					"posting_date": getdate(self.posting_date),
				}
			)
		)

		make_gl_entries(gl_entries, cancel=cancel, merge_entries=False)
