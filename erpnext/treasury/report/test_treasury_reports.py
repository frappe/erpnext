# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# See license.txt

import frappe
from frappe.utils import add_days, getdate, nowdate

from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_term
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.tests.utils import ERPNextTestSuite
from erpnext.treasury.doctype.investment.test_investment import (
	TEST_COMPANY,
	create_financial_institution,
	create_investment_type,
)
from erpnext.treasury.doctype.investment_interest_accrual.investment_interest_accrual import (
	get_accrual_defaults,
)
from erpnext.treasury.doctype.investment_interest_accrual.test_investment_interest_accrual import (
	BOND_TERMS,
	FD_TERMS,
	accrue_all_interest,
	get_investment,
	make_deposit,
	make_fd,
)
from erpnext.treasury.doctype.investment_transaction.test_investment_transaction import (
	BANK_ACCOUNT,
	make_accrual_for_today,
	make_interest_accrual,
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

	def test_position_reports(self):
		_columns, data, *_ = portfolio_statement.execute(self.get_filters(as_on_date=nowdate()))
		self.assertEqual(data[0].book_value, 100000)
		self.assertEqual(data[0].accrued_interest, 500)
		self.assertEqual(data[0].market_value, 100000)

		# nothing was held the day before the purchase
		_columns, data, *_ = portfolio_statement.execute(self.get_filters(as_on_date=add_days(nowdate(), -1)))
		self.assertEqual(data, [])

		_columns, data, *_ = upcoming_maturities.execute(self.get_filters(as_on_date=nowdate()))
		self.assertEqual(data[0].days_to_maturity, 365)
		self.assertEqual(data[0].bucket, "181-365 Days")
		self.assertEqual(data[0].total, 100500)

		# exposure includes the accrued interest
		_columns, data, *_ = investments_by_issuer.execute(self.get_filters(as_on_date=nowdate()))
		self.assertEqual(data[0].issuer, "_Test Bank")
		self.assertEqual(data[0].exposure, 100500)
		self.assertEqual(data[0].share, 100)

		# the purchase was paid from the bank today
		self.assertEqual(get_bank_balance(nowdate()) - get_bank_balance(add_days(nowdate(), -1)), -100000)

	def test_interest_earned_and_received_rolls_forward_receivable(self):
		make_transaction(self.investment.name, "Interest Receipt", interest_amount=200).submit()

		_columns, data, _message, chart = interest_earned_and_received.execute(
			self.get_filters(from_date=nowdate(), to_date=nowdate())
		)

		self.assertEqual(data[0].interest_accrued, 500)
		self.assertEqual(data[0].interest_received, 200)
		self.assertEqual(data[0].closing_receivable, 300)
		self.assertEqual(chart["data"]["datasets"][1]["values"], [200])

		# interest the buyer of a bond pays counts as received
		create_investment_type("_Test Corporate Bond", "Bond")
		investment = make_submitted_investment(**BOND_TERMS)
		make_transaction(investment.name, "Purchase", posting_date="2026-01-01", units=10, rate=1000).submit()
		make_interest_accrual(investment.name, "2026-01-01", "2026-03-31", 2000).submit()
		make_transaction(
			investment.name,
			"Sale",
			posting_date="2026-04-01",
			units=10,
			rate=1200,
			accrued_interest_in_sale=2000,
		).submit()

		_columns, data, _message, _chart = interest_earned_and_received.execute(
			frappe._dict(
				company=TEST_COMPANY, investment=investment.name, from_date="2026-01-01", to_date="2026-04-30"
			)
		)

		self.assertEqual((data[0].interest_received, data[0].closing_receivable), (2000, 0))

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

	def test_cash_flow_forecast_flows(self):
		# the purchased deposit's maturity and interest
		totals = get_forecast_totals(investment_maturity=self.investment.maturity_date)
		self.assertGreaterEqual(totals["Investment Maturities"], 100000)
		self.assertGreater(totals["Investment Interest"], 0)

		before = get_forecast_totals()
		invoice = create_sales_invoice(qty=1, rate=5000)
		make_submitted_investment()  # approved but nothing bought yet
		after = get_forecast_totals()

		self.assertEqual(
			after["Customer Receivables"] - before["Customer Receivables"], invoice.base_grand_total
		)
		self.assertEqual(after["Committed Investments"] - before["Committed Investments"], 100000)

	def test_cash_flow_forecast_expects_each_payment_term_on_its_due_date(self):
		invoice = create_sales_invoice(qty=1, rate=5000, do_not_save=1)
		invoice.due_date = add_days(nowdate(), 60)
		for days in (30, 60):
			create_payment_term(f"_Test {days} Days")
			invoice.append(
				"payment_schedule",
				{
					"payment_term": f"_Test {days} Days",
					"due_date": add_days(nowdate(), days),
					"invoice_portion": 50,
					"payment_amount": 2500,
				},
			)
		invoice.insert().submit()

		receivables = cash_flow_forecast.get_party_flows(TEST_COMPANY)["receivables"]
		for days in (30, 60):
			self.assertIn((getdate(add_days(nowdate(), days)), 2500), receivables)

		# the customer pays the second term, so the first is still expected on its own date
		payment = get_payment_entry("Sales Invoice", invoice.name, party_amount=2500)
		payment.references[0].payment_term = "_Test 60 Days"
		payment.references[0].allocated_amount = 2500
		payment.insert().submit()

		receivables = cash_flow_forecast.get_party_flows(TEST_COMPANY)["receivables"]
		self.assertIn((getdate(add_days(nowdate(), 30)), 2500), receivables)
		self.assertNotIn((getdate(add_days(nowdate(), 60)), 2500), receivables)

		# terms entered as amounts, without a portion, are unpaid too
		invoice = create_sales_invoice(qty=1, rate=3000, do_not_save=1)
		invoice.due_date = add_days(nowdate(), 50)
		for days in (40, 50):
			invoice.append(
				"payment_schedule", {"due_date": add_days(nowdate(), days), "payment_amount": 1500}
			)
		invoice.insert().submit()

		receivables = cash_flow_forecast.get_party_flows(TEST_COMPANY)["receivables"]
		for days in (40, 50):
			self.assertIn((getdate(add_days(nowdate(), days)), 1500), receivables)

	def test_cash_flow_forecast_leaves_out_received_interest(self):
		investment = make_fd(FD_TERMS)
		make_interest_accrual(investment.name, "2026-01-01", "2026-03-31", 1800).submit()
		make_transaction(
			investment.name, "Interest Receipt", posting_date="2026-03-31", interest_amount=1000
		).submit()

		filters = frappe._dict(company=TEST_COMPANY, currency="INR", from_date="2026-01-01")
		flows = cash_flow_forecast.get_interest_flows([get_investment(investment.name)], filters)

		# 800 of the first quarter is still owed, the next quarter in full
		self.assertEqual(flows[:2], [(getdate("2026-03-31"), 800), (getdate("2026-06-30"), 1820)])

	def test_cash_flow_forecast_pays_bought_interest_with_its_coupon(self):
		create_investment_type("_Test Corporate Bond", "Bond")
		investment = make_submitted_investment(**BOND_TERMS)
		make_transaction(investment.name, "Purchase", posting_date="2026-01-01", units=10, rate=1000).submit()
		first_coupon = make_interest_accrual(
			investment.name, **get_accrual_defaults(investment.name)
		).submit()
		make_transaction(
			investment.name,
			"Interest Receipt",
			posting_date="2026-06-30",
			interest_amount=first_coupon.interest_amount,
		).submit()
		make_transaction(
			investment.name,
			"Purchase",
			posting_date="2026-08-01",
			units=5,
			rate=1000,
			accrued_interest_in_purchase=30,
		).submit()

		filters = frappe._dict(company=TEST_COMPANY, currency="INR", from_date="2026-01-01")
		flows = dict(cash_flow_forecast.get_interest_flows([get_investment(investment.name)], filters))
		second_coupon = get_investment(investment.name).interest_schedule[1]

		# the paid first coupon stays paid; the 30 bought comes back with the second coupon
		self.assertNotIn(getdate("2026-06-30"), flows)
		self.assertAlmostEqual(flows[getdate("2026-12-31")], second_coupon.estimated_interest + 30)

	def test_cash_flow_forecast_keeps_unpaid_interest_of_matured_deposit(self):
		investment = make_fd(FD_TERMS)
		accrue_all_interest(investment.name)
		filters = frappe._dict(company=TEST_COMPANY, currency="INR", from_date="2026-01-01")
		before = sum(amount for _date, amount in cash_flow_forecast.get_investment_flows(filters)["interest"])

		make_deposit(investment.name, "Maturity", "2027-01-01", 100000)
		after = sum(amount for _date, amount in cash_flow_forecast.get_investment_flows(filters)["interest"])

		self.assertEqual(before, after)


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
