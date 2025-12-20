# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _, qb
from frappe.query_builder import Criterion
from frappe.query_builder.functions import Sum


class General_Payment_Ledger_Comparison:
	"""
	A Utility report to compare Voucher-wise balance between General and Payment Ledger
	"""

	def __init__(self, filters=None):
		self.filters = filters
		self.gle = []
		self.ple = []

	def get_accounts(self):
		receivable_accounts = [
			x[0]
			for x in frappe.db.get_all(
				"Account",
				filters={"company": self.filters.company, "account_type": "Receivable"},
				as_list=True,
			)
		]
		payable_accounts = [
			x[0]
			for x in frappe.db.get_all(
				"Account", filters={"company": self.filters.company, "account_type": "Payable"}, as_list=True
			)
		]

		self.account_types = frappe._dict(
			{
				"receivable": frappe._dict({"accounts": receivable_accounts, "gle": [], "ple": []}),
				"payable": frappe._dict({"accounts": payable_accounts, "gle": [], "ple": []}),
			}
		)

	def generate_filters(self):
		if self.filters.account:
			self.account_types.receivable.accounts = []
			self.account_types.payable.accounts = []

			for acc in frappe.db.get_all(
				"Account", filters={"name": ["in", self.filters.account]}, fields=["name", "account_type"]
			):
				if acc.account_type == "Receivable":
					self.account_types.receivable.accounts.append(acc.name)
				else:
					self.account_types.payable.accounts.append(acc.name)

	def get_gle(self):
		gle = qb.DocType("GL Entry")

		for acc_type, val in self.account_types.items():
			if val.accounts:
				filter_criterion = []
				if self.filters.voucher_no:
					filter_criterion.append(gle.voucher_no == self.filters.voucher_no)

				if self.filters.period_start_date:
					filter_criterion.append(gle.posting_date.gte(self.filters.period_start_date))

				if self.filters.period_end_date:
					filter_criterion.append(gle.posting_date.lte(self.filters.period_end_date))

				if acc_type == "receivable":
					outstanding = (Sum(gle.debit) - Sum(gle.credit)).as_("outstanding")
				else:
					outstanding = (Sum(gle.credit) - Sum(gle.debit)).as_("outstanding")

				self.account_types[acc_type].gle = (
					qb.from_(gle)
					.select(
						gle.company,
						gle.account,
						gle.voucher_type,
						gle.voucher_no,
						gle.party_type,
						gle.party,
						outstanding,
					)
					.where(
						(gle.company == self.filters.company)
						& (gle.is_cancelled == 0)
						& (gle.account.isin(val.accounts))
					)
					.where(Criterion.all(filter_criterion))
					.groupby(
						gle.company, gle.account, gle.voucher_type, gle.voucher_no, gle.party_type, gle.party
					)
					.run()
				)

	def get_ple(self):
		ple = qb.DocType("Payment Ledger Entry")

		for acc_type, val in self.account_types.items():
			if val.accounts:
				filter_criterion = []
				if self.filters.voucher_no:
					filter_criterion.append(ple.voucher_no == self.filters.voucher_no)

				if self.filters.period_start_date:
					filter_criterion.append(ple.posting_date.gte(self.filters.period_start_date))

				if self.filters.period_end_date:
					filter_criterion.append(ple.posting_date.lte(self.filters.period_end_date))

				self.account_types[acc_type].ple = (
					qb.from_(ple)
					.select(
						ple.company,
						ple.account,
						ple.voucher_type,
						ple.voucher_no,
						ple.party_type,
						ple.party,
						Sum(ple.amount).as_("outstanding"),
					)
					.where(
						(ple.company == self.filters.company)
						& (ple.delinked == 0)
						& (ple.account.isin(val.accounts))
					)
					.where(Criterion.all(filter_criterion))
					.groupby(
						ple.company, ple.account, ple.voucher_type, ple.voucher_no, ple.party_type, ple.party
					)
					.run()
				)

	def compare(self):
		self.gle_balances = set()
		self.ple_balances = set()

		# consolidate both receivable and payable balances in one set
		for _acc_type, val in self.account_types.items():
			self.gle_balances = set(val.gle) | self.gle_balances
			self.ple_balances = set(val.ple) | self.ple_balances

		self.variation_in_payment_ledger = self.gle_balances.difference(self.ple_balances)
		self.variation_in_general_ledger = self.ple_balances.difference(self.gle_balances)
		self.diff = frappe._dict({})

		for x in self.variation_in_payment_ledger:
			self.diff[(x[0], x[1], x[2], x[3], x[4], x[5])] = frappe._dict({"gl_balance": x[6]})

		for x in self.variation_in_general_ledger:
			self.diff.setdefault(
				(x[0], x[1], x[2], x[3], x[4], x[5]), frappe._dict({"gl_balance": 0.0})
			).update(frappe._dict({"pl_balance": x[6]}))

	def generate_data(self):
		self.data = []
		for key, val in self.diff.items():
			self.data.append(
				frappe._dict(
					{
						"company": key[0],
						"account": key[1],
						"voucher_type": key[2],
						"voucher_no": key[3],
						"party_type": key[4],
						"party": key[5],
						"gl_balance": val.gl_balance,
						"pl_balance": val.pl_balance,
					}
				)
			)

	def get_columns(self):
		self.columns = []
		self.columns.append(
			dict(
				label=_("Company"),
				fieldname="company",
				fieldtype="Link",
				options="Company",
				width="100",
			)
		)

		self.columns.append(
			dict(
				label=_("Account"),
				fieldname="account",
				fieldtype="Link",
				options="Account",
				width="100",
			)
		)

		self.columns.append(
			dict(
				label=_("Voucher Type"),
				fieldname="voucher_type",
				fieldtype="Data",
				width="100",
			)
		)

		self.columns.append(
			dict(
				label=_("Voucher No"),
				fieldname="voucher_no",
				fieldtype="Dynamic Link",
				options="voucher_type",
				width="100",
			)
		)

		self.columns.append(
			dict(
				label=_("Party Type"),
				fieldname="party_type",
				fieldtype="Data",
				width="100",
			)
		)

		self.columns.append(
			dict(
				label=_("Party"),
				fieldname="party",
				fieldtype="Dynamic Link",
				options="party_type",
				width="100",
			)
		)

		self.columns.append(
			dict(
				label=_("GL Balance"),
				fieldname="gl_balance",
				fieldtype="Currency",
				options="Company:company:default_currency",
				width="100",
			)
		)

		self.columns.append(
			dict(
				label=_("Payment Ledger Balance"),
				fieldname="pl_balance",
				fieldtype="Currency",
				options="Company:company:default_currency",
				width="100",
			)
		)

	def run(self):
		self.get_accounts()
		self.generate_filters()
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
