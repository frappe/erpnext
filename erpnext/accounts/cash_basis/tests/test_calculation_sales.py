# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Scenarios CB-01 to CB-05, CB-29, CB-30: sales invoices and their payments."""

from erpnext.accounts.cash_basis.tests.cash_basis_case import CashBasisTestCase
from erpnext.accounts.cash_basis.tests.fixtures import CUSTOMER, acc
from erpnext.accounts.cash_basis.tests.vouchers import line, make_advance, make_sales_invoice, pay

SALES = acc("Sales")
SERVICE = acc("Service")
INTEREST = acc("Interest Income")
DEBTORS = acc("Debtors")
BANK = acc("Test Bank")
TAX = acc("ST 6%")
UNAPPLIED = acc("Test Unapplied Receipts")


class TestCashBasisSales(CashBasisTestCase):
	def test_cb01_invoice_without_payment(self):
		make_sales_invoice("2026-03-01", [line(100)])
		self.assert_balances(
			"2026-03-31",
			accrual={SALES: -100, DEBTORS: 100},
			cash={SALES: 0, DEBTORS: 0},
		)

	def test_cb02_full_payment_in_same_period(self):
		invoice = make_sales_invoice("2026-03-01", [line(100)])
		pay(invoice, "2026-03-15")
		balances = {SALES: -100, DEBTORS: 0, BANK: 100}
		self.assert_balances("2026-03-31", accrual=balances, cash=balances)
		self.assert_invariants("2026-03-31", fully_paid=True)

	def test_cb03_part_payment_in_later_period(self):
		invoice = make_sales_invoice("2026-03-01", [line(100)])
		pay(invoice, "2026-04-10", 40)
		self.assert_balances("2026-03-31", from_date="2026-03-01", accrual={SALES: -100}, cash={SALES: 0})
		self.assert_balances(
			"2026-04-30", from_date="2026-04-01", accrual={SALES: 0, BANK: 40}, cash={SALES: -40, BANK: 40}
		)
		self.assert_balances("2026-04-30", accrual={DEBTORS: 60}, cash={DEBTORS: 0, SALES: -40})

	def test_cb04_receivable_remainder_is_unpaid_tax(self):
		invoice = make_sales_invoice("2026-03-01", [line(100)], taxes=[(TAX, 10)])
		pay(invoice, "2026-04-10", 55)
		self.assert_balances(
			"2026-03-31",
			accrual={SALES: -100, DEBTORS: 110, TAX: -10},
			cash={SALES: 0, DEBTORS: 10, TAX: -10},
		)
		# Section 6.5 worked example: income 50, receivable 5, tax 10, bank 55.
		self.assert_balances(
			"2026-04-30",
			accrual={SALES: -100, DEBTORS: 55, TAX: -10, BANK: 55},
			cash={SALES: -50, DEBTORS: 5, TAX: -10, BANK: 55},
		)

	def test_cb05_two_lines_two_cost_centers(self):
		main, second = acc("Main"), acc("Second")
		invoice = make_sales_invoice(
			"2026-03-01",
			[line(60, account=SALES, cost_center=main), line(40, account=SERVICE, cost_center=second)],
		)
		pay(invoice, "2026-04-10", 50)
		self.assert_balances(
			"2026-04-30", accrual={SALES: -60, SERVICE: -40}, cash={SALES: -30, SERVICE: -20}
		)
		by_cost_center = {}
		for row in self.adjustments("2026-04-30"):
			if row["account"] in (SALES, SERVICE):
				key = (row["account"], row["cost_center"])
				by_cost_center[key] = round(by_cost_center.get(key, 0) + row["debit"] - row["credit"], 2)
		# Adjustments: deferral of the full line, then recognition of half of it.
		self.assertEqual(by_cost_center, {(SALES, main): 30.0, (SERVICE, second): 20.0})

	def test_cb29_rounding_of_three_part_payments(self):
		invoice = make_sales_invoice(
			"2026-03-01",
			[line(33.33, account=SALES), line(33.33, account=SERVICE), line(33.34, account=INTEREST)],
		)
		pay(invoice, "2026-03-10", 33.33)
		# Each line: 33.33 * 33.33 / 100 = 11.11, and 33.34 * 0.3333 = 11.11.
		self.assert_balances("2026-03-10", cash={SALES: -11.11, SERVICE: -11.11, INTEREST: -11.11})
		pay(invoice, "2026-03-20", 33.33)
		self.assert_balances("2026-03-20", cash={SALES: -22.22, SERVICE: -22.22, INTEREST: -22.22})
		pay(invoice, "2026-03-30", 33.34)
		# The cumulative target of each line is the line itself at full settlement, so no remainder stays.
		self.assert_balances(
			"2026-03-31",
			accrual={SALES: -33.33, SERVICE: -33.33, INTEREST: -33.34, DEBTORS: 0},
			cash={SALES: -33.33, SERVICE: -33.33, INTEREST: -33.34, DEBTORS: 0},
		)
		self.assert_invariants("2026-03-31", fully_paid=True)

	def test_cb30_overpayment(self):
		invoice = make_sales_invoice("2026-03-01", [line(100)])
		payment = make_advance("Customer", CUSTOMER, "2026-03-10", 120, submit=False)
		payment.append(
			"references",
			{"reference_doctype": "Sales Invoice", "reference_name": invoice.name, "allocated_amount": 100},
		)
		payment.save()
		payment.submit()
		self.assert_balances(
			"2026-03-31",
			accrual={SALES: -100, DEBTORS: -20, BANK: 120},
			cash={SALES: -100, UNAPPLIED: -20, DEBTORS: 0, BANK: 120},
		)
