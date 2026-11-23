# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Base class for the cash basis calculation tests, with the invariant checks of section 11."""

from collections import defaultdict

import frappe
from frappe.query_builder.functions import Sum
from frappe.utils import flt, getdate

from erpnext.accounts.cash_basis.calculation import (
	UNAPPLIED_INCOME_AND_EXPENSE,
	get_cash_adjustments,
	get_exceptions,
)
from erpnext.accounts.cash_basis.tests.fixtures import (
	TEST_UNAPPLIED_PAYMENTS,
	TEST_UNAPPLIED_RECEIPTS,
	US_COMPANY,
	put_test_countries_in_scope,
	setup_cash_basis_master_data,
)
from erpnext.tests.utils import ERPNextTestSuite

PRECISION = 2


class CashBasisTestCase(ERPNextTestSuite):
	"""The calculation gets the unapplied treatment and accounts as arguments, not from Company."""

	treatment = UNAPPLIED_INCOME_AND_EXPENSE

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		put_test_countries_in_scope(cls)
		setup_cash_basis_master_data()

	def setUp(self):
		self.unapplied_arguments = {
			"unapplied_treatment": self.treatment,
			"unapplied_accounts": {"Customer": TEST_UNAPPLIED_RECEIPTS, "Supplier": TEST_UNAPPLIED_PAYMENTS},
		}
		self.unapplied_accounts = {TEST_UNAPPLIED_RECEIPTS, TEST_UNAPPLIED_PAYMENTS}

	# Balances. A balance is debit less credit.

	def adjustments(self, to_date, from_date=None, group_by="row"):
		return get_cash_adjustments(
			US_COMPANY, to_date, from_date, group_by=group_by, filters={}, **self.unapplied_arguments
		)

	def accrual_balances(self, to_date, from_date=None) -> dict:
		gle = frappe.qb.DocType("GL Entry")
		query = (
			frappe.qb.from_(gle)
			.select(gle.account, Sum(gle.debit - gle.credit).as_("balance"))
			.where((gle.company == US_COMPANY) & (gle.is_cancelled == 0) & (gle.posting_date <= to_date))
			.groupby(gle.account)
		)
		if from_date:
			query = query.where(gle.posting_date >= from_date)
		return {row.account: flt(row.balance, PRECISION) for row in query.run(as_dict=True)}

	def cash_balances(self, to_date, from_date=None) -> dict:
		balances = defaultdict(float, self.accrual_balances(to_date, from_date))
		for account, amount in adjustment_totals(self.adjustments(to_date, from_date)).items():
			balances[account] = flt(balances[account] + amount, PRECISION)
		return balances

	def assert_balances(self, to_date, accrual=None, cash=None, from_date=None):
		"""Hand-calculated balances for each method. An account that is not named is not checked."""
		for method, expected, balances in (
			("Accrual", accrual or {}, self.accrual_balances(to_date, from_date)),
			("Cash", cash or {}, self.cash_balances(to_date, from_date)),
		):
			for account, amount in expected.items():
				self.assertAlmostEqual(
					flt(balances.get(account, 0.0), PRECISION),
					amount,
					places=PRECISION,
					msg=f"{method} balance of {account} from {from_date} to {to_date}",
				)
		self.assert_invariants(to_date, from_date)

	def exception_reasons(self, to_date="2026-12-31") -> dict:
		return {e["voucher_no"]: e["reason"] for e in get_exceptions(US_COMPANY, to_date)}

	def deferred_cash_balances(self, to_date, from_date=None) -> dict:
		"""The expected cash basis balance of each deferred account, from queries of the test.

		On the cash basis, only the invoices that are exceptions keep their rows on a deferred
		account, with their schedule Journal Entries. The rows of a converted invoice, of a return
		that settles it, and of their schedules net to zero.
		"""
		accounts = get_deferred_accounts()
		if not accounts:
			return {}
		exceptions = {e["voucher_no"] for e in get_exceptions(US_COMPANY, to_date)}
		# A return that settles an exception invoice keeps its deferred row with it.
		for doctype in ("Sales Invoice", "Purchase Invoice"):
			exceptions.update(
				frappe.get_all(
					doctype,
					filters={
						"company": US_COMPANY,
						"docstatus": 1,
						"is_return": 1,
						"update_outstanding_for_self": 0,
						"return_against": ("in", list(exceptions) or [""]),
					},
					pluck="name",
				)
			)
		gle = frappe.qb.DocType("GL Entry")
		query = (
			frappe.qb.from_(gle)
			.select(gle.account, Sum(gle.debit - gle.credit))
			.where(
				(gle.company == US_COMPANY)
				& (gle.is_cancelled == 0)
				& (gle.posting_date <= to_date)
				& gle.account.isin(list(accounts))
			)
			.groupby(gle.account)
		)
		if from_date:
			query = query.where(gle.posting_date >= from_date)
		balances = dict.fromkeys(accounts, 0.0)
		if exceptions:
			own = gle.voucher_no.isin(list(exceptions))
			schedule = (gle.voucher_subtype.isin(["Deferred Revenue", "Deferred Expense"])) & (
				gle.against_voucher.isin(list(exceptions))
			)
			for account, amount in query.where(own | schedule).run():
				balances[account] = flt(amount, PRECISION)
		return balances

	# Invariants of section 11.

	def assert_invariants(self, to_date, from_date=None, fully_paid=False):
		rows = self.adjustments(to_date, from_date)
		cumulative = self.adjustments(to_date)
		accounts = frappe.get_all(
			"Account",
			filters={"company": US_COMPANY},
			fields=["name", "account_type", "report_type"],
		)
		details = {a.name: a for a in accounts}
		# The closing account of a PCV holds the cash retained earnings (section 6.11).
		closing_accounts = set(
			frappe.get_all(
				"Period Closing Voucher",
				filters={"company": US_COMPANY, "docstatus": 1},
				pluck="closing_account_head",
			)
		)
		excluded = self.unapplied_accounts | closing_accounts
		for label, selected, start in (("period", rows, from_date), ("cumulative", cumulative, None)):
			totals = adjustment_totals(selected)
			deferred = self.deferred_cash_balances(to_date, start)
			deferred_accounts = set(deferred)
			accrual = self.accrual_balances(to_date, start)
			# I1: the cash basis trial balance balances.
			self.assertAlmostEqual(sum(totals.values()), 0.0, places=PRECISION, msg=f"I1 ({label})")
			party_total = pl_total = 0.0
			# I6 compares the pairs before the closing transfer of section 6.11.
			before_closing = adjustment_totals(
				[r for r in selected if r["voucher_type"] != "Period Closing Voucher"]
			)
			for account, amount in totals.items():
				account_type, report_type = details[account].account_type, details[account].report_type
				if account_type in ("Bank", "Cash"):
					self.assertAlmostEqual(amount, 0.0, places=PRECISION, msg=f"I2 {account} ({label})")
				is_party = account_type in ("Receivable", "Payable")
				if account in deferred_accounts:
					# I3 for a deferred account: only the exception invoices keep their rows.
					cash = flt(accrual.get(account, 0.0) + amount, PRECISION)
					self.assertAlmostEqual(cash, deferred[account], places=PRECISION, msg=f"I3 {account}")
				elif report_type != "Profit and Loss" and not is_party and account not in excluded:
					self.assertAlmostEqual(amount, 0.0, places=PRECISION, msg=f"I3 {account} ({label})")
			for account in deferred_accounts - set(totals):
				cash = flt(accrual.get(account, 0.0), PRECISION)
				self.assertAlmostEqual(cash, deferred[account], places=PRECISION, msg=f"I3 {account}")
			for account, amount in before_closing.items():
				if details[account].account_type in ("Receivable", "Payable"):
					party_total += amount
				# A deferred account takes the place of the convertible line (phase 7).
				if details[account].report_type == "Profit and Loss" or account in deferred_accounts:
					pl_total += amount
			# I6: party adjustments are the negative of the P&L adjustments.
			self.assertAlmostEqual(party_total, -pl_total, places=PRECISION, msg=f"I6 ({label})")
			if fully_paid:
				for account, amount in totals.items():
					self.assertAlmostEqual(amount, 0.0, places=PRECISION, msg=f"I4 {account}")
		# I8: the totals for each account are the same with and without the dimension group-by.
		grouped = adjustment_totals(self.adjustments(to_date, from_date, group_by="account"))
		by_row = adjustment_totals(rows)
		for account in set(grouped) | set(by_row):
			self.assertAlmostEqual(
				grouped.get(account, 0.0), by_row.get(account, 0.0), places=PRECISION, msg="I8"
			)
		for row in rows:
			self.assertEqual(row["is_cash_adjustment"], 1)
			if from_date:
				self.assertGreaterEqual(row["posting_date"], getdate(from_date))
			self.assertLessEqual(row["posting_date"], getdate(to_date))


def get_deferred_accounts() -> set[str]:
	"""The deferred accounts of the submitted deferred items of the test company."""
	accounts = set()
	for item_doctype, parent, flag, field in (
		("Sales Invoice Item", "Sales Invoice", "enable_deferred_revenue", "deferred_revenue_account"),
		("Purchase Invoice Item", "Purchase Invoice", "enable_deferred_expense", "deferred_expense_account"),
	):
		item, invoice = frappe.qb.DocType(item_doctype), frappe.qb.DocType(parent)
		accounts.update(
			frappe.qb.from_(item)
			.join(invoice)
			.on(invoice.name == item.parent)
			.select(item[field])
			.distinct()
			.where((invoice.company == US_COMPANY) & (invoice.docstatus == 1) & (item[flag] == 1))
			.run(pluck=True)
		)
	return accounts


def adjustment_totals(rows) -> dict:
	totals = defaultdict(float)
	for row in rows:
		totals[row["account"]] += flt(row["debit"]) - flt(row["credit"])
	return {account: flt(amount, PRECISION) for account, amount in totals.items()}
