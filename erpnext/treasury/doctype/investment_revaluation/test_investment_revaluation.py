# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# See license.txt

import frappe
from frappe.utils import add_days, nowdate

from erpnext.tests.utils import ERPNextTestSuite
from erpnext.treasury.doctype.investment.test_investment import (
	TEST_COMPANY,
	create_financial_institution,
	create_investment_type,
	make_investment,
)
from erpnext.treasury.doctype.investment_transaction.test_investment_transaction import (
	make_submitted_investment,
	make_transaction,
)

FAIR_VALUE_ACCOUNT = "Earnest Money - _TC"
UNREALISED_ACCOUNT = "Service - _TC"
RESERVE_ACCOUNT = "Revaluation Surplus - _TC"
REVALUATION_ACCOUNTS = {
	"fair_value_adjustment_account": FAIR_VALUE_ACCOUNT,
	"unrealised_gain_loss_account": UNREALISED_ACCOUNT,
	"fair_value_reserve_account": RESERVE_ACCOUNT,
}


class TestInvestmentRevaluation(ERPNextTestSuite):
	def setUp(self):
		create_investment_type("_Test Bank FD", "Deposit")
		create_investment_type("_Test Equity Fund", "Units")
		create_financial_institution("_Test Bank")

	def test_market_revaluation_posts_unrealised_gain(self):
		investment = make_fund_investment("FVTPL")
		revaluation = make_market_revaluation(investment.name, nav_per_unit=12).submit()

		row = revaluation.investments[0]
		self.assertEqual((row.book_value, row.market_value, row.unrealised_gain_loss), (1000, 1200, 200))
		self.assertEqual(
			get_gl_entries(revaluation.name), {FAIR_VALUE_ACCOUNT: (200, 0), UNREALISED_ACCOUNT: (0, 200)}
		)

		investment.reload()
		self.assertEqual((investment.unrealised_gain_loss, investment.market_value), (200, 1200))

	def test_next_revaluation_posts_only_the_change(self):
		investment = make_fund_investment("FVOCI")
		make_market_revaluation(investment.name, nav_per_unit=12).submit()

		revaluation = make_market_revaluation(investment.name, nav_per_unit=11, days=1).submit()

		self.assertEqual(revaluation.investments[0].previous_gain_loss, 200)
		self.assertEqual(revaluation.investments[0].adjustment_amount, -100)
		self.assertEqual(
			get_gl_entries(revaluation.name), {RESERVE_ACCOUNT: (100, 0), FAIR_VALUE_ACCOUNT: (0, 100)}
		)

	def test_fvoci_gain_goes_to_equity_reserve_until_sold(self):
		investment = make_fund_investment("FVOCI")
		revaluation = make_market_revaluation(investment.name, nav_per_unit=12).submit()

		self.assertEqual(
			get_gl_entries(revaluation.name), {FAIR_VALUE_ACCOUNT: (200, 0), RESERVE_ACCOUNT: (0, 200)}
		)

		# a full sale moves the reserve to profit and loss
		sale = make_transaction(
			investment.name, "Sale", units=100, rate=12, posting_date=add_days(nowdate(), 1)
		).submit()

		self.assertEqual(sale.realised_gain_loss, 200)
		entries = get_transaction_gl_entries(sale.name)
		self.assertEqual((entries[FAIR_VALUE_ACCOUNT], entries[RESERVE_ACCOUNT]), ((0, 200), (200, 0)))
		self.assertEqual(frappe.db.get_value("Investment", investment.name, "unrealised_gain_loss"), 0)

	def test_invalid_revaluation_is_rejected(self):
		# the fair value reserve must be an equity account
		investment = make_investment(
			investment_type="_Test Equity Fund",
			measurement_category="FVOCI",
			**{**REVALUATION_ACCOUNTS, "fair_value_reserve_account": UNREALISED_ACCOUNT},
		)
		self.assertRaises(frappe.ValidationError, investment.insert)

		# deposits have no market value
		deposit = make_deposit_investment("Amortized Cost")
		self.assertRaises(frappe.ValidationError, make_market_revaluation(deposit.name).insert)

		# the revaluation stays in the investment's finance book
		if not frappe.db.exists("Finance Book", "_Test Treasury Book"):
			frappe.get_doc({"doctype": "Finance Book", "finance_book_name": "_Test Treasury Book"}).insert()
		fund = make_fund_investment("FVTPL")
		revaluation = make_market_revaluation(fund.name, nav_per_unit=12)
		revaluation.finance_book = "_Test Treasury Book"
		self.assertRaises(frappe.ValidationError, revaluation.insert)

	def test_amortized_cost_market_revaluation_posts_no_gl(self):
		investment = make_fund_investment("Amortized Cost")
		revaluation = make_market_revaluation(investment.name, nav_per_unit=12).submit()

		self.assertEqual(revaluation.investments[0].posts_to_ledger, 0)
		self.assertEqual(get_gl_entries(revaluation.name), {})
		self.assertEqual(frappe.db.get_value("Investment", investment.name, "unrealised_gain_loss"), 200)

	def test_revaluations_and_exits_stay_in_date_order(self):
		investment = make_fund_investment("FVTPL")
		first = make_market_revaluation(investment.name, nav_per_unit=12).submit()
		second = make_market_revaluation(investment.name, nav_per_unit=15, days=2).submit()

		backdated = make_market_revaluation(investment.name, nav_per_unit=11, days=1)
		self.assertRaises(frappe.ValidationError, backdated.insert)
		# only the latest revaluation can be cancelled
		self.assertRaises(frappe.ValidationError, first.cancel)

		# the revaluation valued the units held at the end of its date
		for days in (1, 2):
			with self.subTest(days=days):
				sale = make_transaction(
					investment.name, "Sale", units=50, rate=12, posting_date=add_days(nowdate(), days)
				)
				self.assertRaises(frappe.ValidationError, sale.submit)

		second.cancel()
		self.assertEqual(get_gl_entries(second.name), {})
		self.assertEqual(frappe.db.get_value("Investment", investment.name, "unrealised_gain_loss"), 200)

		make_transaction(
			investment.name, "Sale", units=50, rate=12, posting_date=add_days(nowdate(), 3)
		).submit()
		# a revaluation cannot be dated before an exit it did not see, nor cancelled after one
		missed_exit = make_market_revaluation(investment.name, nav_per_unit=12, days=2)
		self.assertRaises(frappe.ValidationError, missed_exit.insert().submit)
		self.assertRaises(frappe.ValidationError, first.cancel)

		# the next day's exit of all units takes the whole gain off
		valued_at_cost = make_fund_investment("Amortized Cost")
		make_market_revaluation(valued_at_cost.name, nav_per_unit=12).submit()
		make_transaction(
			valued_at_cost.name, "Sale", units=100, rate=12, posting_date=add_days(nowdate(), 1)
		).submit()
		valued_at_cost.reload()
		self.assertEqual((valued_at_cost.unrealised_gain_loss, valued_at_cost.market_value), (0, 0))

	def test_sale_takes_its_share_of_fvtpl_gain_off_the_books(self):
		investment = make_fund_investment("FVTPL")
		make_market_revaluation(investment.name, nav_per_unit=12).submit()

		# half the units go, so half the 200 gain is taken off; the sale books it again as realised
		sale = make_transaction(
			investment.name, "Sale", units=50, rate=12, posting_date=add_days(nowdate(), 1)
		).submit()

		self.assertEqual(sale.realised_gain_loss, 100)
		entries = get_transaction_gl_entries(sale.name)
		self.assertEqual((entries[FAIR_VALUE_ACCOUNT], entries[UNREALISED_ACCOUNT]), ((0, 100), (100, 0)))
		investment.reload()
		self.assertEqual((investment.unrealised_gain_loss, investment.market_value), (100, 600))

	def test_next_revaluation_starts_from_what_the_sale_left(self):
		investment = make_fund_investment("FVTPL")
		make_market_revaluation(investment.name, nav_per_unit=12).submit()
		make_transaction(
			investment.name, "Sale", units=50, rate=12, posting_date=add_days(nowdate(), 1)
		).submit()

		# 50 units at 13 = 650 against a cost of 500 is 150; 100 is still on the books
		revaluation = make_market_revaluation(investment.name, nav_per_unit=13, days=2).submit()

		row = revaluation.investments[0]
		self.assertEqual(
			(row.unrealised_gain_loss, row.previous_gain_loss, row.adjustment_amount), (150, 100, 50)
		)

	def test_amortized_cost_gain_stays_with_the_valued_units(self):
		investment = make_fund_investment("Amortized Cost")
		make_market_revaluation(investment.name, nav_per_unit=12).submit()

		# the 100 new units were bought at 12, so they carry no gain of their own
		make_transaction(
			investment.name, "Purchase", units=100, rate=12, posting_date=add_days(nowdate(), 1)
		).submit()

		investment.reload()
		self.assertEqual((investment.unrealised_gain_loss, investment.market_value), (200, 2400))

	def test_get_investments_loads_only_what_can_be_revalued(self):
		if not frappe.db.exists("Finance Book", "_Test Treasury Book"):
			frappe.get_doc({"doctype": "Finance Book", "finance_book_name": "_Test Treasury Book"}).insert()

		in_book = make_fund_investment("FVTPL", finance_book="_Test Treasury Book")
		in_no_book = make_fund_investment("FVTPL")
		revaluation = frappe.get_doc(
			{
				"doctype": "Investment Revaluation",
				"company": TEST_COMPANY,
				"finance_book": "_Test Treasury Book",
			}
		)
		revaluation.set_investments()

		loaded = {row.investment for row in revaluation.investments}
		self.assertIn(in_book.name, loaded)
		self.assertNotIn(in_no_book.name, loaded)

		# an exited investment has no gain left to revalue
		make_market_revaluation(in_no_book.name, nav_per_unit=12).submit()
		make_transaction(
			in_no_book.name, "Sale", units=100, rate=12, posting_date=add_days(nowdate(), 1)
		).submit()

		revaluation = frappe.get_doc(
			{
				"doctype": "Investment Revaluation",
				"company": TEST_COMPANY,
				"revaluation_date": add_days(nowdate(), 2),
			}
		)
		revaluation.set_investments()
		self.assertNotIn(in_no_book.name, [row.investment for row in revaluation.investments])


def make_fund_investment(measurement_category, **args):
	"""Equity fund investment of 100 units bought at 10."""
	investment = make_submitted_investment(
		investment_type="_Test Equity Fund",
		measurement_category=measurement_category,
		**REVALUATION_ACCOUNTS,
		**args,
	)
	make_transaction(investment.name, "Purchase", units=100, rate=10).submit()
	return investment


def make_deposit_investment(measurement_category):
	investment = make_submitted_investment(measurement_category=measurement_category, **REVALUATION_ACCOUNTS)
	make_transaction(investment.name, "Purchase", gross_amount=100000).submit()
	return investment


def make_market_revaluation(investment, days=0, **row):
	return frappe.get_doc(
		{
			"doctype": "Investment Revaluation",
			"company": TEST_COMPANY,
			"revaluation_date": add_days(nowdate(), days),
			"investments": [{"investment": investment, **row}],
		}
	)


def get_transaction_gl_entries(voucher_no):
	entries = frappe.get_all(
		"GL Entry",
		filters={"voucher_type": "Investment Transaction", "voucher_no": voucher_no, "is_cancelled": 0},
		fields=["account", "debit", "credit"],
	)
	return {entry.account: (entry.debit, entry.credit) for entry in entries}


def get_gl_entries(voucher_no):
	entries = frappe.get_all(
		"GL Entry",
		filters={"voucher_type": "Investment Revaluation", "voucher_no": voucher_no, "is_cancelled": 0},
		fields=["account", "debit", "credit"],
	)
	return {entry.account: (entry.debit, entry.credit) for entry in entries}
