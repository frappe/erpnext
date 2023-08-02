# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import qb


class General_Payment_Ledger_Comparison(object):
	"""
	Compare Voucher-wise entries between General and Payment Ledger
	"""

	def __init__(self, filters=None):
		self.filters = filters
		self.gle = []
		self.ple = []

	def get_accounts(self):
		self.accounts = frappe.db.get_all(
			"Account",
			filters={"company": self.filters.company, "account_type": ["in", ["Receivable", "Payable"]]},
		)

	def get_gle(self):
		gle = qb.DocType("GL Entry")
		self.gle = (
			qb.from_(gle)
			.select("*")
			.where(
				(gle.company == self.filters.company)
				& (gle.is_cancelled == 0)
				& (gle.account.isin(self.accounts))
			)
			.run()
		)

	def get_ple(self):
		ple = qb.DocType("Payment Ledger Entry")
		self.ple = (
			qb.from_(ple)
			.select("*")
			.where(
				(ple.company == self.filters.company)
				& (ple.delinked == 0)
				& (ple.accounts.isin(self.accounts))
			)
			.run()
		)

	def compare(self):
		pass

	def run(self):
		self.get_accounts()
		self.get_gle()
		self.get_ple()
		self.compare()
		# self.generate_diff()


def execute(filters=None):
	columns, data = [], []

	rpt = General_Payment_Ledger_Comparison(filters)
	columns, data = rpt.run()

	return columns, data
