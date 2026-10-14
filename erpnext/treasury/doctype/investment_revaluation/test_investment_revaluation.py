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

	def test_fvoci_gain_goes_to_equity_reserve(self):
		investment = make_fund_investment("FVOCI")
		revaluation = make_market_revaluation(investment.name, nav_per_unit=12).submit()

		self.assertEqual(
			get_gl_entries(revaluation.name), {FAIR_VALUE_ACCOUNT: (200, 0), RESERVE_ACCOUNT: (0, 200)}
		)

	def test_fair_value_reserve_must_be_equity(self):
		investment = make_investment(
			investment_type="_Test Equity Fund",
			measurement_category="FVOCI",
			**{**REVALUATION_ACCOUNTS, "fair_value_reserve_account": UNREALISED_ACCOUNT},
		)

		self.assertRaises(frappe.ValidationError, investment.insert)

	def test_amortized_cost_market_revaluation_posts_no_gl(self):
		investment = make_fund_investment("Amortized Cost")
		revaluation = make_market_revaluation(investment.name, nav_per_unit=12).submit()

		self.assertEqual(revaluation.investments[0].posts_to_ledger, 0)
		self.assertEqual(get_gl_entries(revaluation.name), {})
		self.assertEqual(frappe.db.get_value("Investment", investment.name, "unrealised_gain_loss"), 200)

	def test_market_revaluation_does_not_apply_to_deposits(self):
		investment = make_deposit_investment("Amortized Cost")
		revaluation = make_market_revaluation(investment.name)
		self.assertRaises(frappe.ValidationError, revaluation.insert)

	def test_revaluation_cannot_be_back_dated(self):
		investment = make_fund_investment("FVTPL")
		make_market_revaluation(investment.name, nav_per_unit=12, days=1).submit()

		revaluation = make_market_revaluation(investment.name, nav_per_unit=11)
		self.assertRaises(frappe.ValidationError, revaluation.insert)

	def test_only_latest_revaluation_can_be_cancelled(self):
		investment = make_fund_investment("FVTPL")
		first = make_market_revaluation(investment.name, nav_per_unit=12).submit()
		second = make_market_revaluation(investment.name, nav_per_unit=15, days=1).submit()

		self.assertRaises(frappe.ValidationError, first.cancel)

		second.cancel()
		self.assertEqual(get_gl_entries(second.name), {})
		self.assertEqual(frappe.db.get_value("Investment", investment.name, "unrealised_gain_loss"), 200)

	def test_sale_takes_its_share_of_fvtpl_gain_off_the_books(self):
		investment = make_fund_investment("FVTPL")
		make_market_revaluation(investment.name, nav_per_unit=12).submit()

		# half the units go, so half the 200 gain is taken off; the sale books it again as realised
		sale = make_transaction(investment.name, "Sale", units=50, rate=12).submit()

		self.assertEqual(sale.realised_gain_loss, 100)
		entries = get_transaction_gl_entries(sale.name)
		self.assertEqual((entries[FAIR_VALUE_ACCOUNT], entries[UNREALISED_ACCOUNT]), ((0, 100), (100, 0)))
		investment.reload()
		self.assertEqual((investment.unrealised_gain_loss, investment.market_value), (100, 600))

	def test_full_sale_moves_fvoci_reserve_to_profit_and_loss(self):
		investment = make_fund_investment("FVOCI")
		make_market_revaluation(investment.name, nav_per_unit=12).submit()

		sale = make_transaction(investment.name, "Sale", units=100, rate=12).submit()

		self.assertEqual(sale.realised_gain_loss, 200)
		entries = get_transaction_gl_entries(sale.name)
		self.assertEqual((entries[FAIR_VALUE_ACCOUNT], entries[RESERVE_ACCOUNT]), ((0, 200), (200, 0)))
		self.assertEqual(frappe.db.get_value("Investment", investment.name, "unrealised_gain_loss"), 0)

	def test_next_revaluation_starts_from_what_the_sale_left(self):
		investment = make_fund_investment("FVTPL")
		make_market_revaluation(investment.name, nav_per_unit=12).submit()
		make_transaction(investment.name, "Sale", units=50, rate=12).submit()

		# 50 units at 13 = 650 against a cost of 500 is 150; 100 is still on the books
		revaluation = make_market_revaluation(investment.name, nav_per_unit=13, days=1).submit()

		row = revaluation.investments[0]
		self.assertEqual(
			(row.unrealised_gain_loss, row.previous_gain_loss, row.adjustment_amount), (150, 100, 50)
		)

	def test_exit_and_revaluation_follow_each_other_in_order(self):
		investment = make_fund_investment("FVTPL")
		revaluation = make_market_revaluation(investment.name, nav_per_unit=12, days=2).submit()

		sale = make_transaction(
			investment.name, "Sale", units=50, rate=12, posting_date=add_days(nowdate(), 1)
		)
		self.assertRaises(frappe.ValidationError, sale.submit)

		make_transaction(
			investment.name, "Sale", units=50, rate=12, posting_date=add_days(nowdate(), 3)
		).submit()
		self.assertRaises(frappe.ValidationError, revaluation.cancel)

	def test_exited_investment_has_no_gain_left_to_revalue(self):
		investment = make_fund_investment("FVTPL")
		make_market_revaluation(investment.name, nav_per_unit=12).submit()
		make_transaction(investment.name, "Sale", units=100, rate=12).submit()

		revaluation = frappe.get_doc(
			{
				"doctype": "Investment Revaluation",
				"company": TEST_COMPANY,
				"revaluation_date": add_days(nowdate(), 1),
			}
		)
		revaluation.set_investments()
		self.assertNotIn(investment.name, [row.investment for row in revaluation.investments])


def make_fund_investment(measurement_category):
	"""Equity fund investment of 100 units bought at 10."""
	investment = make_submitted_investment(
		investment_type="_Test Equity Fund", measurement_category=measurement_category, **REVALUATION_ACCOUNTS
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
