# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _, qb
from frappe.query_builder.functions import Sum


class General_Payment_Ledger_Comparison(object):
	"""
	Compare Voucher-wise entries between General and Payment Ledger
	"""

	def __init__(self, filters=None):
		self.filters = filters
		self.gle = []
		self.ple = []

	def get_accounts(self):
		receivable_accounts = frappe.db.get_all(
			"Account", filters={"company": self.filters.company, "account_type": "Receivable"}, as_list=True
		)
		payable_accounts = frappe.db.get_all(
			"Account", filters={"company": self.filters.company, "account_type": "Payable"}, as_list=True
		)

		self.account_types = frappe._dict(
			{
				"receivable": frappe._dict({"accounts": receivable_accounts, "gle": [], "ple": []}),
				"payable": frappe._dict({"accounts": payable_accounts, "gle": [], "ple": []}),
			}
		)

	def get_gle(self):
		gle = qb.DocType("GL Entry")

		for acc_type, val in self.account_types.items():
			if acc_type == "receivable":
				outstanding = (Sum(gle.debit) - Sum(gle.credit)).as_("outstanding")
			else:
				outstanding = (Sum(gle.credit) - Sum(gle.debit)).as_("outstanding")

			self.account_types[acc_type].gle = (
				qb.from_(gle)
				.select(
					gle.company,
					gle.account,
					gle.voucher_no,
					outstanding,
				)
				.where(
					(gle.company == self.filters.company)
					& (gle.is_cancelled == 0)
					& (gle.account.isin(val.accounts))
				)
				.groupby(gle.company, gle.account, gle.voucher_no, gle.party)
				# .run(as_dict=True)
				.run()
			)

	def get_ple(self):
		ple = qb.DocType("Payment Ledger Entry")

		for acc_type, val in self.account_types.items():
			self.account_types[acc_type].ple = (
				qb.from_(ple)
				.select(ple.company, ple.account, ple.voucher_no, Sum(ple.amount).as_("outstanding"))
				.where(
					(ple.company == self.filters.company) & (ple.delinked == 0) & (ple.account.isin(val.accounts))
				)
				.groupby(ple.company, ple.account, ple.voucher_no, ple.party)
				# .run(as_dict=True)
				.run()
			)

	def compare(self):
		self.gle_balances = set()
		self.ple_balances = set()

		# consolidate both receivable and payable balances in one set
		for acc_type, val in self.account_types.items():
			self.gle_balances = set(val.gle) | self.gle_balances
			self.ple_balances = set(val.ple) | self.ple_balances

		self.diff1 = self.gle_balances.difference(self.ple_balances)
		self.diff2 = self.ple_balances.difference(self.gle_balances)
		self.diff = frappe._dict({})

		for x in self.diff1:
			self.diff[(x[0], x[1], x[2])] = frappe._dict({"gl_balance": x[3]})

		for x in self.diff2:
			self.diff[(x[0], x[1], x[2])].update(frappe._dict({"pl_balance": x[3]}))

	def generate_data(self):
		self.data = []
		for key, val in self.diff.items():
			self.data.append(
				frappe._dict(
					{"voucher_no": key[2], "gl_balance": val.gl_balance, "pl_balance": val.pl_balance}
				)
			)

	def get_columns(self):
		self.columns = []
		options = None
		self.columns.append(
			dict(
				label=_("Voucher No"),
				fieldname="voucher_no",
				fieldtype="Data",
				options=options,
				width="100",
			)
		)

		self.columns.append(
			dict(
				label=_("GL Balance"), fieldname="gl_balance", fieldtype="data", options=options, width="100"
			)
		)

		self.columns.append(
			dict(
				label=_("Payment Ledger Balance"),
				fieldname="pl_balance",
				fieldtype="data",
				options=options,
				width="100",
			)
		)

	def run(self):
		self.get_accounts()
		self.get_gle()
		self.get_ple()
		self.compare()
		self.generate_data()
		self.get_columns()

		return self.columns, self.data


def execute(filters=None):
	columns, data = [], []

	rpt = General_Payment_Ledger_Comparison(filters)
	columns, data = rpt.run()

	return columns, data
