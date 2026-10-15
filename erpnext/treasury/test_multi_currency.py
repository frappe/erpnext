# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# See license.txt

"""USD investments in an INR company: vouchers hold USD, the ledger gets USD times the Exchange Rate."""

from unittest.mock import patch

import frappe
from frappe.tests import freeze_time
from frappe.utils import add_days, getdate, nowdate

from erpnext.tests.utils import ERPNextTestSuite
from erpnext.treasury.doctype.investment.test_investment import (
	TEST_COMPANY,
	create_financial_institution,
	create_investment_type,
)
from erpnext.treasury.doctype.investment_interest_accrual.investment_interest_accrual import (
	make_draft_accruals,
)
from erpnext.treasury.doctype.investment_interest_accrual.test_investment_interest_accrual import FD_TERMS
from erpnext.treasury.doctype.investment_revaluation.test_investment_revaluation import (
	REVALUATION_ACCOUNTS,
	UNREALISED_ACCOUNT,
	make_market_revaluation,
)
from erpnext.treasury.doctype.investment_transaction.test_investment_transaction import (
	BANK_ACCOUNT,
	get_gl_entries,
	make_interest_accrual,
	make_submitted_investment,
	make_transaction,
)
from erpnext.treasury.report.cash_flow_forecast.cash_flow_forecast import get_investment_flows

USD_BANK_ACCOUNT = "_Test Bank USD - _TC"
EUR_BANK_ACCOUNT = "_Test Bank EUR - _TC"
USD_INVESTMENT_ACCOUNT = "_Test Investments USD - _TC"
INVESTMENT_ACCOUNT = "Short-term Investments - _TC"
BOND_TERMS = {
	"investment_type": "_Test Corporate Bond",
	"purchase_date": "2026-01-01",
	"maturity_date": "2028-01-01",
	"face_value": 1000,
	"coupon_rate": 8,
	"coupon_frequency": "Semi-Annual",
}


class TestMultiCurrencyInvestment(ERPNextTestSuite):
	def setUp(self):
		create_investment_type("_Test Bank FD", "Deposit")
		create_investment_type("_Test Equity Fund", "Units")
		create_investment_type("_Test Corporate Bond", "Bond")
		create_financial_institution("_Test Bank")
		create_usd_investment_account()

	def test_purchase_posts_company_currency_and_bank_currency(self):
		investment = make_usd_investment()
		purchase = make_usd_transaction(
			investment.name, "Purchase", 83, gross_amount=1000, charges=10, cash_account=USD_BANK_ACCOUNT
		).submit()

		self.assertEqual(purchase.net_amount, 1010)
		self.assertEqual(
			get_gl_entries(purchase.name),
			{INVESTMENT_ACCOUNT: (83000, 0), "Bank Charges - _TC": (830, 0), USD_BANK_ACCOUNT: (0, 83830)},
		)
		# the USD bank moves by the USD amount, the INR accounts by the INR amount
		self.assertEqual(get_account_currency_entries(purchase.name)[USD_BANK_ACCOUNT], ("USD", 0, 1010))
		self.assertEqual(get_account_currency_entries(purchase.name)[INVESTMENT_ACCOUNT], ("INR", 83000, 0))

	def test_foreign_currency_investment_account_keeps_foreign_amount(self):
		"""A USD investment account moves by USD 1,000 and by its INR value at the same time."""
		investment = make_usd_investment(investment_account=USD_INVESTMENT_ACCOUNT)
		purchase = make_usd_transaction(
			investment.name, "Purchase", 80, gross_amount=1000, cash_account=USD_BANK_ACCOUNT
		).submit()

		self.assertEqual(
			get_account_currency_entries(purchase.name)[USD_INVESTMENT_ACCOUNT], ("USD", 1000, 0)
		)
		self.assertEqual(get_gl_entries(purchase.name)[USD_INVESTMENT_ACCOUNT], (80000, 0))

		maturity = make_usd_transaction(investment.name, "Maturity", 85, gross_amount=1000).submit()

		self.assertEqual(get_gl_entries(maturity.name)[USD_INVESTMENT_ACCOUNT], (0, 80000))
		self.assertEqual(
			get_account_currency_entries(maturity.name)[USD_INVESTMENT_ACCOUNT], ("USD", 0, 1000)
		)

		# paid from an INR bank, the INR accounts move by the INR amount only
		investment = make_usd_investment()
		purchase = make_usd_transaction(investment.name, "Purchase", 83, gross_amount=1000).submit()
		self.assertEqual(
			get_gl_entries(purchase.name), {INVESTMENT_ACCOUNT: (83000, 0), BANK_ACCOUNT: (0, 83000)}
		)

	def test_invalid_foreign_currency_entry_is_rejected(self):
		investment = make_usd_investment()
		eur_purchase = make_usd_transaction(
			investment.name, "Purchase", 83, gross_amount=1000, cash_account=EUR_BANK_ACCOUNT
		).insert()
		# a bank in a third currency
		self.assertRaises(frappe.ValidationError, eur_purchase.submit)

		make_usd_transaction(investment.name, "Purchase", 83, gross_amount=1000).submit()
		# no exchange rate
		for entry in (
			make_transaction(investment.name, "Purchase", gross_amount=1000),
			make_interest_accrual(investment.name, nowdate(), nowdate(), 50),
		):
			with self.subTest(entry.doctype):
				self.assertRaises(frappe.ValidationError, entry.insert)

		fund = make_usd_investment(
			investment_type="_Test Equity Fund", measurement_category="FVTPL", **REVALUATION_ACCOUNTS
		)
		make_usd_transaction(fund.name, "Purchase", 80, units=100, rate=10).submit()
		revaluation = make_market_revaluation(fund.name, nav_per_unit=12)
		self.assertRaises(frappe.ValidationError, revaluation.insert)

	def test_approved_amount_is_in_investment_currency(self):
		investment = make_usd_investment(approved_amount=1000)
		make_usd_transaction(investment.name, "Purchase", 83, gross_amount=1000).submit()

		additional = make_usd_transaction(investment.name, "Purchase", 83, gross_amount=1)
		self.assertRaises(frappe.ValidationError, additional.insert)

	def test_interest_accrued_and_received_at_same_rate(self):
		investment = make_usd_investment()
		make_usd_transaction(investment.name, "Purchase", 83, gross_amount=1000).submit()

		accrual = make_usd_accrual(investment.name, 50, 83)
		self.assertEqual(
			get_gl_entries(accrual.name, "Investment Interest Accrual"),
			{"Earnest Money - _TC": (4150, 0), "Interest on Fixed Deposits - _TC": (0, 4150)},
		)

		receipt = make_usd_transaction(
			investment.name,
			"Interest Receipt",
			83,
			interest_amount=50,
			tax_withheld=5,
			cash_account=USD_BANK_ACCOUNT,
		).submit()
		self.assertEqual(
			get_gl_entries(receipt.name),
			{
				USD_BANK_ACCOUNT: (3735, 0),
				"Prepaid Expenses - _TC": (415, 0),
				"Earnest Money - _TC": (0, 4150),
			},
		)
		self.assertEqual(get_account_currency_entries(receipt.name)[USD_BANK_ACCOUNT], ("USD", 45, 0))
		self.assertEqual(get_investment(investment.name).accrued_interest, 0)

	def test_market_revaluation_translates_fair_value(self):
		investment = make_usd_investment(
			investment_type="_Test Equity Fund",
			measurement_category="FVTPL",
			**{**REVALUATION_ACCOUNTS, "fair_value_adjustment_account": USD_INVESTMENT_ACCOUNT},
		)
		make_usd_transaction(investment.name, "Purchase", 80, units=100, rate=10).submit()

		# NAV moves 10 -> 12 USD and the rupee moves 80 -> 82, both are in the fair value
		revaluation = make_market_revaluation(investment.name, nav_per_unit=12, conversion_rate=82).submit()

		row = revaluation.investments[0]
		self.assertEqual((row.book_value, row.market_value, row.unrealised_gain_loss), (80000, 98400, 18400))
		self.assertEqual(
			get_gl_entries(revaluation.name, "Investment Revaluation"),
			{USD_INVESTMENT_ACCOUNT: (18400, 0), UNREALISED_ACCOUNT: (0, 18400)},
		)
		# INR 18,400 at 82 is USD 224.39 in the USD account
		self.assertEqual(
			get_account_currency_entries(revaluation.name)[USD_INVESTMENT_ACCOUNT], ("USD", 224.39, 0)
		)

	def test_company_currency_ignores_exchange_rate(self):
		"""An INR investment in an INR company has nothing to convert, whatever rate is typed in."""
		investment = make_submitted_investment()
		purchase = make_usd_transaction(investment.name, "Purchase", 2, gross_amount=1000).submit()

		self.assertEqual(purchase.conversion_rate, 1)
		self.assertEqual(
			get_gl_entries(purchase.name), {INVESTMENT_ACCOUNT: (1000, 0), BANK_ACCOUNT: (0, 1000)}
		)

		fund = make_submitted_investment(
			investment_type="_Test Equity Fund", measurement_category="FVTPL", **REVALUATION_ACCOUNTS
		)
		make_transaction(fund.name, "Purchase", units=100, rate=10).submit()
		revaluation = make_market_revaluation(fund.name, nav_per_unit=12, conversion_rate=5).insert()

		row = revaluation.investments[0]
		self.assertEqual((row.conversion_rate, row.market_value), (1, 1200))

	def test_renewal_keeps_investment_currency(self):
		investment = make_usd_investment()
		make_usd_transaction(investment.name, "Purchase", 83, gross_amount=1000).submit()
		make_usd_transaction(investment.name, "Maturity", 83, gross_amount=1000).submit()

		renewal = frappe.get_doc(
			{
				"doctype": "Investment Renewal",
				"original_investment": investment.name,
				"renewal_date": nowdate(),
				"principal_renewed": 1000,
			}
		).submit()

		self.assertEqual(renewal.currency, "USD")
		self.assertEqual(frappe.db.get_value("Investment", renewal.new_investment, "currency"), "USD")

	def test_daily_job_takes_draft_exchange_rate_from_currency_exchange(self):
		make_currency_exchange("USD", "INR", 83, "2026-03-31")
		investment = make_usd_investment(**FD_TERMS)
		make_usd_transaction(
			investment.name, "Purchase", 80, posting_date="2026-01-01", gross_amount=1000
		).submit()

		# the job commits after each investment, which would keep this test's records
		with freeze_time("2026-07-15"), patch.object(frappe.db, "commit"):
			make_draft_accruals()

		self.assertEqual(
			frappe.db.get_value(
				"Investment Interest Accrual",
				{"investment": investment.name, "docstatus": 0},
				"conversion_rate",
			),
			83,
		)

	def test_position_is_in_company_currency(self):
		"""Total Cost and the other position figures come from the ledger, so they are shown in INR."""
		investment = make_usd_investment()
		make_usd_transaction(investment.name, "Purchase", 83, gross_amount=1000).submit()

		investment.reload()
		self.assertEqual((investment.company_currency, investment.total_cost), ("INR", 83000))
		for fieldname in ("total_cost", "accrued_interest", "market_value", "unrealised_gain_loss"):
			self.assertEqual(investment.meta.get_field(fieldname).options, "company_currency")

	def test_bond_discount_is_kept_in_investment_currency(self):
		"""10 bonds of face value USD 1,000 bought at USD 950: book value INR 788,500 plus the USD 500
		discount at 83 is the face value of INR 830,000."""
		investment = make_usd_investment(**BOND_TERMS)
		make_usd_transaction(
			investment.name, "Purchase", 83, posting_date="2026-01-01", units=10, rate=950
		).submit()

		self.assertEqual(get_investment(investment.name).unamortised_premium_discount, 500)

		filters = frappe._dict(company=TEST_COMPANY, currency="INR", from_date=nowdate())
		with patch(f"{get_investment_flows.__module__}.get_exchange_rate", return_value=83):
			maturities = get_investment_flows(filters)["maturities"]

		self.assertIn((getdate("2028-01-01"), 830000), maturities)

	def test_maturity_at_new_rate_books_exchange_gain_or_loss(self):
		"""Cost leaves the investment account at the purchase rate; the rate change is an exchange gain or loss."""
		investment = make_usd_investment()
		make_usd_transaction(investment.name, "Purchase", 80, gross_amount=1000).submit()

		maturity = make_usd_transaction(investment.name, "Maturity", 85, gross_amount=1000).submit()

		self.assertEqual(
			get_gl_entries(maturity.name),
			{BANK_ACCOUNT: (85000, 0), INVESTMENT_ACCOUNT: (0, 80000), get_exchange_account(): (0, 5000)},
		)
		investment.reload()
		self.assertEqual((investment.total_cost, investment.status), (0, "Matured"))

		investment = make_usd_investment()
		make_usd_transaction(investment.name, "Purchase", 80, gross_amount=1000).submit()

		maturity = make_usd_transaction(investment.name, "Maturity", 78, gross_amount=1000).submit()

		self.assertEqual(
			get_gl_entries(maturity.name),
			{BANK_ACCOUNT: (78000, 0), INVESTMENT_ACCOUNT: (0, 80000), get_exchange_account(): (2000, 0)},
		)
		self.assertEqual(get_investment(investment.name).total_cost, 0)

	def test_partial_withdrawal_leaves_at_average_booked_rate(self):
		"""USD 600 at 80 and USD 400 at 85 are booked at INR 82,000, so half of it leaves at INR 41,000."""
		investment = make_usd_investment()
		make_usd_transaction(investment.name, "Purchase", 80, gross_amount=600).submit()
		make_usd_transaction(investment.name, "Purchase", 85, gross_amount=400).submit()

		withdrawal = make_usd_transaction(investment.name, "Withdrawal", 90, gross_amount=500).submit()

		self.assertEqual(
			get_gl_entries(withdrawal.name),
			{BANK_ACCOUNT: (45000, 0), INVESTMENT_ACCOUNT: (0, 41000), get_exchange_account(): (0, 4000)},
		)
		investment.reload()
		self.assertEqual((investment.total_cost, investment.status), (41000, "Partially Redeemed"))

	def test_fund_sale_splits_market_gain_and_exchange_gain(self):
		"""NAV 10 -> 12 USD is a market gain at today's rate; rate 80 -> 85 on the cost is an exchange gain."""
		investment = make_usd_investment(investment_type="_Test Equity Fund")
		make_usd_transaction(investment.name, "Purchase", 80, units=100, rate=10).submit()

		sale = make_usd_transaction(investment.name, "Sale", 85, units=100, rate=12).submit()

		self.assertEqual(
			get_gl_entries(sale.name),
			{
				BANK_ACCOUNT: (102000, 0),
				INVESTMENT_ACCOUNT: (0, 80000),
				"Gain/Loss on Asset Disposal - _TC": (0, 17000),
				get_exchange_account(): (0, 5000),
			},
		)
		investment.reload()
		self.assertEqual((investment.total_cost, investment.status), (0, "Redeemed"))

	def test_interest_received_at_new_rate_books_exchange_gain(self):
		investment = make_usd_investment()
		make_usd_transaction(investment.name, "Purchase", 82, gross_amount=1000).submit()
		make_usd_accrual(investment.name, 50, 82)

		later = make_usd_transaction(
			investment.name, "Interest Receipt", 84, interest_amount=30, posting_date=add_days(nowdate(), 10)
		).submit()
		# 30 of the 50 accrued at 82 is INR 2,460, received at 84 as INR 2,520
		self.assertEqual(
			get_gl_entries(later.name),
			{BANK_ACCOUNT: (2520, 0), "Earnest Money - _TC": (0, 2460), get_exchange_account(): (0, 60)},
		)

		# dated before the receipt above, so it settles 20 of the 50 held then: 4,100 * 20 / 50
		earlier = make_usd_transaction(
			investment.name, "Interest Receipt", 84, interest_amount=20, posting_date=add_days(nowdate(), 5)
		).submit()

		self.assertEqual(
			get_gl_entries(earlier.name),
			{BANK_ACCOUNT: (1680, 0), "Earnest Money - _TC": (0, 1640), get_exchange_account(): (0, 40)},
		)
		self.assertEqual(get_investment(investment.name).accrued_interest, 0)

	def test_cancel_exit_restores_booked_value(self):
		investment = make_usd_investment()
		make_usd_transaction(investment.name, "Purchase", 80, gross_amount=1000).submit()
		maturity = make_usd_transaction(investment.name, "Maturity", 85, gross_amount=1000).submit()

		maturity.cancel()

		self.assertFalse(get_gl_entries(maturity.name))
		investment.reload()
		self.assertEqual((investment.total_cost, investment.status), (80000, "Active"))

	def test_exchange_difference_needs_company_account(self):
		investment = make_usd_investment()
		make_usd_transaction(investment.name, "Purchase", 80, gross_amount=1000).submit()
		frappe.db.set_value("Company", TEST_COMPANY, "exchange_gain_loss_account", None)
		frappe.clear_document_cache("Company", TEST_COMPANY)
		# the rollback after the test restores the account, but not the cached Company
		self.addCleanup(frappe.clear_document_cache, "Company", TEST_COMPANY)

		maturity = make_usd_transaction(investment.name, "Maturity", 85, gross_amount=1000).insert()
		self.assertRaises(frappe.ValidationError, maturity.submit)


def make_usd_investment(**args):
	return make_submitted_investment(currency="USD", **args)


def make_usd_transaction(investment, transaction_type, conversion_rate, **args):
	return make_transaction(investment, transaction_type, conversion_rate=conversion_rate, **args)


def make_usd_accrual(investment, interest_amount, conversion_rate):
	return make_interest_accrual(
		investment, nowdate(), nowdate(), interest_amount, conversion_rate=conversion_rate
	).submit()


def get_exchange_account():
	return frappe.get_cached_value("Company", TEST_COMPANY, "exchange_gain_loss_account")


def get_investment(name):
	return frappe.get_doc("Investment", name)


def get_account_currency_entries(voucher_no):
	entries = frappe.get_all(
		"GL Entry",
		filters={"voucher_no": voucher_no, "is_cancelled": 0},
		fields=["account", "account_currency", "debit_in_account_currency", "credit_in_account_currency"],
	)
	return {
		entry.account: (
			entry.account_currency,
			entry.debit_in_account_currency,
			entry.credit_in_account_currency,
		)
		for entry in entries
	}


def create_usd_investment_account():
	if frappe.db.exists("Account", USD_INVESTMENT_ACCOUNT):
		return

	frappe.get_doc(
		{
			"doctype": "Account",
			"account_name": "_Test Investments USD",
			"parent_account": frappe.db.get_value("Account", INVESTMENT_ACCOUNT, "parent_account"),
			"company": TEST_COMPANY,
			"account_currency": "USD",
		}
	).insert()


def make_currency_exchange(from_currency, to_currency, exchange_rate, date):
	frappe.get_doc(
		{
			"doctype": "Currency Exchange",
			"date": date,
			"from_currency": from_currency,
			"to_currency": to_currency,
			"exchange_rate": exchange_rate,
			"for_buying": 1,
			"for_selling": 1,
		}
	).insert()
