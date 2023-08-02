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
		self.receivable_accounts = frappe.db.get_all(
			"Account", filters={"company": self.filters.company, "account_type": "Receivable"}, as_list=True
		)
		self.payable_accounts = frappe.db.get_all(
			"Account", filters={"company": self.filters.company, "account_type": "Payable"}, as_list=True
		)

	def get_gle(self):
		gle = qb.DocType("GL Entry")
		self.receivable_gle = (
			qb.from_(gle)
			.select(
				gle.company,
				gle.account,
				gle.voucher_no,
				gle.voucher_no,
				(Sum(gle.debit) - Sum(gle.credit)).as_("outstanding"),
			)
			.where(
				(gle.company == self.filters.company)
				& (gle.is_cancelled == 0)
				& (gle.account.isin(self.receivable_accounts))
			)
			.groupby(gle.company, gle.account, gle.voucher_no, gle.party)
			# .run(as_dict=True)
			.run()
		)

		self.payable_gle = (
			qb.from_(gle)
			.select(
				gle.company,
				gle.account,
				gle.voucher_no,
				gle.voucher_no,
				(Sum(gle.credit) - Sum(gle.debit)).as_("outstanding"),
			)
			.where(
				(gle.company == self.filters.company)
				& (gle.is_cancelled == 0)
				& (gle.account.isin(self.payable_accounts))
			)
			.groupby(gle.company, gle.account, gle.voucher_no, gle.party)
			# .run(as_dict=True)
			.run()
		)

	def get_ple(self):
		ple = qb.DocType("Payment Ledger Entry")
		self.receivable_ple = (
			qb.from_(ple)
			.select(
				ple.company, ple.account, ple.voucher_no, ple.voucher_no, Sum(ple.amount).as_("outstanding")
			)
			.where(
				(ple.company == self.filters.company)
				& (ple.delinked == 0)
				& (ple.account.isin(self.receivable_accounts))
			)
			.groupby(ple.company, ple.account, ple.voucher_no, ple.party)
			# .run(as_dict=True)
			.run()
		)

		self.payable_ple = (
			qb.from_(ple)
			.select(
				ple.company, ple.account, ple.voucher_no, ple.voucher_no, Sum(ple.amount).as_("outstanding")
			)
			.where(
				(ple.company == self.filters.company)
				& (ple.delinked == 0)
				& (ple.account.isin(self.payable_accounts))
			)
			.groupby(ple.company, ple.account, ple.voucher_no, ple.party)
			# .run(as_dict=True)
			.run()
		)

	def compare(self):
		self.gle_balances = set()
		self.ple_balances = set()
		for x in self.receivable_gle:
			self.gle_balances.add(x)
		for x in self.payable_gle:
			self.gle_balances.add(x)

		for x in self.receivable_ple:
			self.ple_balances.add(x)
		for x in self.payable_ple:
			self.ple_balances.add(x)

		self.diff1 = self.gle_balances.difference(self.ple_balances)
		self.diff2 = self.ple_balances.difference(self.gle_balances)
		self.diff = frappe._dict({})

		self.data = []
		for x in self.diff1:
			self.diff[(x[0], x[1], x[2], x[3])] = frappe._dict({"gl_balance": x[4]})

		for x in self.diff2:
			self.diff[(x[0], x[1], x[2], x[3])].update(frappe._dict({"pl_balance": x[4]}))

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
		self.get_columns()

		return self.columns, self.data


def execute(filters=None):
	columns, data = [], []

	rpt = General_Payment_Ledger_Comparison(filters)
	columns, data = rpt.run()

	return columns, data
