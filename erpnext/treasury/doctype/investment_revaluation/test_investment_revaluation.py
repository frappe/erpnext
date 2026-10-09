# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# See license.txt

import frappe
from frappe.utils import add_days, nowdate

from erpnext.tests.utils import ERPNextTestSuite
from erpnext.treasury.doctype.investment.test_investment import (
	TEST_COMPANY,
	create_financial_institution,
	create_investment_type,
)
from erpnext.treasury.doctype.investment_transaction.test_investment_transaction import (
	make_submitted_investment,
	make_transaction,
)

FAIR_VALUE_ACCOUNT = "Earnest Money - _TC"
UNREALISED_ACCOUNT = "Revaluation Surplus - _TC"
REVALUATION_ACCOUNTS = {
	"fair_value_adjustment_account": FAIR_VALUE_ACCOUNT,
	"unrealised_gain_loss_account": UNREALISED_ACCOUNT,
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
			get_gl_entries(revaluation.name), {UNREALISED_ACCOUNT: (100, 0), FAIR_VALUE_ACCOUNT: (0, 100)}
		)

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

	def test_get_investments_clears_gain_of_exited_investment(self):
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
		self.assertIn(investment.name, [row.investment for row in revaluation.investments])

		revaluation.set(
			"investments", [row for row in revaluation.investments if row.investment == investment.name]
		)
		revaluation.insert().submit()

		self.assertEqual(revaluation.investments[0].adjustment_amount, -200)
		self.assertEqual(frappe.db.get_value("Investment", investment.name, "unrealised_gain_loss"), 0)


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


def get_gl_entries(voucher_no):
	entries = frappe.get_all(
		"GL Entry",
		filters={"voucher_type": "Investment Revaluation", "voucher_no": voucher_no, "is_cancelled": 0},
		fields=["account", "debit", "credit"],
	)
	return {entry.account: (entry.debit, entry.credit) for entry in entries}
