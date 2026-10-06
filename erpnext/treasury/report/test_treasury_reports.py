# Copyright (c) 2026, Aagnya Mistry and contributors
# See license.txt

import frappe
from frappe.utils import add_days, getdate, nowdate

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.tests.utils import ERPNextTestSuite
from erpnext.treasury.doctype.investment.test_investment import (
	TEST_COMPANY,
	create_financial_institution,
	create_investment_type,
)
from erpnext.treasury.doctype.investment_transaction.test_investment_transaction import (
	BANK_ACCOUNT,
	make_accrual_for_today,
	make_submitted_investment,
	make_transaction,
)
from erpnext.treasury.report.bank_and_cash_balances import bank_and_cash_balances
from erpnext.treasury.report.cash_flow_forecast import cash_flow_forecast
from erpnext.treasury.report.interest_earned_and_received import interest_earned_and_received
from erpnext.treasury.report.investment_returns import investment_returns
from erpnext.treasury.report.investments_by_issuer import investments_by_issuer
from erpnext.treasury.report.portfolio_statement import portfolio_statement
from erpnext.treasury.report.upcoming_maturities import upcoming_maturities


class TestTreasuryReports(ERPNextTestSuite):
	def setUp(self):
		create_investment_type("_Test Bank FD", "Deposit")
		create_financial_institution("_Test Bank")

		self.investment = make_submitted_investment()
		make_transaction(self.investment.name, "Purchase", gross_amount=100000).submit()
		make_accrual_for_today(self.investment.name, 500)

	def get_filters(self, **filters):
		return frappe._dict(company=TEST_COMPANY, investment=self.investment.name, **filters)

	def test_portfolio_statement(self):
		_columns, data, *_ = portfolio_statement.execute(self.get_filters(as_on_date=nowdate()))

		self.assertEqual(data[0].book_value, 100000)
		self.assertEqual(data[0].accrued_interest, 500)
		self.assertEqual(data[0].market_value, 100000)

	def test_portfolio_statement_before_purchase_is_empty(self):
		_columns, data, *_ = portfolio_statement.execute(self.get_filters(as_on_date=add_days(nowdate(), -1)))

		self.assertEqual(data, [])

	def test_upcoming_maturities_bucket(self):
		_columns, data, *_ = upcoming_maturities.execute(self.get_filters(as_on_date=nowdate()))

		self.assertEqual(data[0].days_to_maturity, 365)
		self.assertEqual(data[0].bucket, "181-365 Days")
		self.assertEqual(data[0].total, 100500)

	def test_investments_by_issuer_includes_accrued_interest(self):
		_columns, data, *_ = investments_by_issuer.execute(self.get_filters(as_on_date=nowdate()))

		self.assertEqual(data[0].issuer, "_Test Bank")
		self.assertEqual(data[0].exposure, 100500)
		self.assertEqual(data[0].share, 100)

	def test_interest_earned_and_received_rolls_forward_receivable(self):
		make_transaction(self.investment.name, "Interest Receipt", interest_amount=200).submit()

		_columns, data, _message, chart = interest_earned_and_received.execute(
			self.get_filters(from_date=nowdate(), to_date=nowdate())
		)

		self.assertEqual(data[0].interest_accrued, 500)
		self.assertEqual(data[0].interest_received, 200)
		self.assertEqual(data[0].closing_receivable, 300)
		self.assertEqual(chart["data"]["datasets"][1]["values"], [200])

	def test_investment_returns(self):
		_columns, data, _message, chart = investment_returns.execute(
			self.get_filters(from_date=nowdate(), to_date=nowdate())
		)

		self.assertEqual(data[0].purchases, 100000)
		self.assertEqual(data[0].average_invested, 100000)
		self.assertEqual(data[0].interest_income, 500)
		self.assertEqual(data[0].return_percent, 0.5)
		self.assertEqual(chart["data"]["datasets"][0]["values"], [500])

	def test_investment_returns_shows_exchange_gain_loss(self):
		"""100 fund units bought at USD 10 when USD 1 = INR 80 and sold at USD 12 when USD 1 = INR 85."""
		create_investment_type("_Test Equity Fund", "Units")
		investment = make_submitted_investment(investment_type="_Test Equity Fund", currency="USD")
		make_transaction(investment.name, "Purchase", units=100, rate=10, conversion_rate=80).submit()
		make_transaction(investment.name, "Sale", units=100, rate=12, conversion_rate=85).submit()

		_columns, data, *_ = investment_returns.execute(
			frappe._dict(
				company=TEST_COMPANY, investment=investment.name, from_date=nowdate(), to_date=nowdate()
			)
		)

		self.assertEqual(data[0].realised_gain_loss, 17000)
		self.assertEqual(data[0].exchange_gain_loss, 5000)
		self.assertEqual(data[0].total_return, 22000)

	def test_bank_and_cash_balances_reflects_purchase_payment(self):
		today = get_bank_balance(nowdate())
		yesterday = get_bank_balance(add_days(nowdate(), -1))

		self.assertEqual(today - yesterday, -100000)

	def test_cash_flow_forecast_flows(self):
		before = get_forecast_totals()
		invoice = create_sales_invoice(qty=1, rate=5000)
		make_submitted_investment()  # approved but nothing bought yet
		after = get_forecast_totals()

		self.assertEqual(
			after["Customer Receivables"] - before["Customer Receivables"], invoice.base_grand_total
		)
		self.assertEqual(after["Committed Investments"] - before["Committed Investments"], 100000)

	def test_cash_flow_forecast_includes_maturity_and_interest(self):
		totals = get_forecast_totals(investment_maturity=self.investment.maturity_date)

		self.assertGreaterEqual(totals["Investment Maturities"], 100000)
		self.assertGreater(totals["Investment Interest"], 0)


def get_bank_balance(as_on_date):
	_columns, data = bank_and_cash_balances.execute(frappe._dict(company=TEST_COMPANY, as_on_date=as_on_date))
	return next((row.balance for row in data if row.account == BANK_ACCOUNT), 0)


def get_forecast_totals(investment_maturity=None):
	periods = 1
	if investment_maturity:
		periods = 13 + (getdate(investment_maturity).year - getdate(nowdate()).year) * 12

	_columns, data = cash_flow_forecast.execute(
		frappe._dict(
			company=TEST_COMPANY,
			from_date=nowdate(),
			periodicity="Monthly",
			periods=periods,
			include_overdue=1,
		)
	)
	return {row["category"]: row.get("total", 0) for row in data}
