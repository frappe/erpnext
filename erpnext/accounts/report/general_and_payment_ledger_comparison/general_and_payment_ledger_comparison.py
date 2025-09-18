# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json

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
						gle.posting_date,
						gle.docstatus,
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
						ple.posting_date,
						ple.docstatus,
						Sum(ple.amount).as_("outstanding"),
					)
					.where(
						(ple.company == self.filters.company)
						& (ple.delinked == 0)
						& (ple.account.isin(val.accounts))
					)
					.where(Criterion.all(filter_criterion))
					.groupby(
						ple.company,
						ple.account,
						ple.voucher_type,
						ple.voucher_no,
						ple.party_type,
						ple.party,
						ple.posting_date,
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

		gl_map = {
			(x[0], x[1], x[2], x[3], x[4], x[5]): {
				"posting_date": x[6],
				"docstatus": x[7],
				"balance": x[8] or 0,
			}
			for x in self.gle_balances
		}
		pl_map = {
			(x[0], x[1], x[2], x[3], x[4], x[5]): {
				"posting_date": x[6],
				"docstatus": x[7],
				"balance": x[8] or 0,
			}
			for x in self.ple_balances
		}

		self.diff = frappe._dict()
		all_keys = set(gl_map.keys()) | set(pl_map.keys())

		for key in all_keys:
			gl_entry = gl_map.get(key, {})
			pl_entry = pl_map.get(key, {})

			gl_balance = gl_entry.get("balance", 0)
			pl_balance = pl_entry.get("balance", 0)
			posting_date = gl_entry.get("posting_date") or pl_entry.get("posting_date")
			docstatus = gl_entry.get("docstatus") or pl_entry.get("docstatus")

			self.diff[
				(posting_date, key[0], key[1], key[2], key[3], docstatus, key[4], key[5])
			] = frappe._dict(
				{
					"gl_balance": gl_balance,
					"pl_balance": pl_balance,
				}
			)

	def generate_data(self):
		self.data = []
		for key, val in self.diff.items():
			difference = (val.gl_balance or 0) - (val.pl_balance or 0)

			if abs(difference) != 0:
				self.data.append(
					frappe._dict(
						{
							"posting_date": key[0],
							"company": key[1],
							"account": key[2],
							"voucher_type": key[3],
							"voucher_no": key[4],
							"docstatus": key[5],
							"party_type": key[6],
							"party": key[7],
							"gl_balance": val.gl_balance,
							"pl_balance": val.pl_balance,
							"difference": difference,
						}
					)
				)

	def get_columns(self):
		self.columns = []

		self.columns.append(
			dict(
				label=_("Posting Date"),
				fieldname="posting_date",
				fieldtype="Date",
				width="100",
			)
		)

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
				label=_("Status"),
				fieldname="docstatus",
				fieldtype="Data",
				width="80",
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

		self.columns.append(
			dict(
				label=_("Difference"),
				fieldname="difference",
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

	status_map = {0: "Draft", 1: "Submitted", 2: "Cancelled"}
	for row in data:
		if "docstatus" in row:
			row["docstatus"] = status_map.get(row["docstatus"], row["docstatus"])

	return columns, data


@frappe.whitelist()
def repost_ledger(docs, delete_existing=0, company=None):
	docs = json.loads(docs) if isinstance(docs, str) else docs
	delete_existing = int(delete_existing)

	ral = frappe.new_doc("Repost Accounting Ledger")
	ral.company = company
	ral.delete_cancelled_entries = delete_existing

	for doc in docs:
		ral.append("vouchers", {"voucher_type": doc.get("voucher_type"), "voucher_no": doc.get("voucher_no")})

	ral.insert()
	ral.submit()
	return ral.name
