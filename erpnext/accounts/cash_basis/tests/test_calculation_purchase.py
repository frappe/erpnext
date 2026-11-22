# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Scenarios CB-06, CB-13, CB-14, CB-19: purchase invoices."""

import frappe

from erpnext.accounts.cash_basis.tests.cash_basis_case import CashBasisTestCase
from erpnext.accounts.cash_basis.tests.fixtures import SUPPLIER, US_COMPANY, acc
from erpnext.accounts.cash_basis.tests.vouchers import (
	BANK,
	line,
	make_journal_entry,
	make_purchase_invoice,
	pay,
)

RENT = acc("Office Rent")
CREDITORS = acc("Creditors")
EQUIPMENT = acc("Office Equipment")


class TestCashBasisPurchase(CashBasisTestCase):
	def test_cb06_purchase_invoice_part_payment(self):
		invoice = make_purchase_invoice("2026-03-01", [line(200)])
		pay(invoice, "2026-04-10", 50)
		self.assert_balances("2026-03-31", from_date="2026-03-01", accrual={RENT: 200}, cash={RENT: 0})
		self.assert_balances(
			"2026-04-30", from_date="2026-04-01", accrual={RENT: 0, BANK: -50}, cash={RENT: 50, BANK: -50}
		)
		self.assert_balances("2026-04-30", accrual={CREDITORS: -150}, cash={CREDITORS: 0})

	def test_cb13_purchase_invoice_is_paid(self):
		make_purchase_invoice(
			"2026-03-01",
			[line(100)],
			is_paid=1,
			cash_bank_account=BANK,
			paid_amount=100,
			mode_of_payment="Cash",
		)
		balances = {RENT: 100, CREDITORS: 0, BANK: -100}
		self.assert_balances("2026-03-31", accrual=balances, cash=balances)
		self.assert_invariants("2026-03-31", fully_paid=True)

	def test_cb14_tax_withheld_at_source(self):
		tds_account = frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": "TDS Payable",
				"parent_account": acc("Duties and Taxes"),
				"company": US_COMPANY,
				"account_type": "Tax",
			}
		).insert()
		category = frappe.get_doc(
			{
				"doctype": "Tax Withholding Category",
				"name": "_Test Cash Basis TDS",
				"category_name": "_Test Cash Basis TDS",
				"rates": [
					{
						"from_date": "2026-01-01",
						"to_date": "2026-12-31",
						"tax_withholding_rate": 10,
						"single_threshold": 0,
						"cumulative_threshold": 0,
					}
				],
				"accounts": [{"company": US_COMPANY, "account": tds_account.name}],
			}
		).insert()
		frappe.db.set_value("Supplier", SUPPLIER, "tax_withholding_category", category.name)
		invoice = make_purchase_invoice(
			"2026-03-01", [line(1000)], apply_tds=1, tax_withholding_category=category.name
		)
		self.assertEqual(invoice.taxes_and_charges_deducted, 100)

		# The tax withheld is a cash settlement on the invoice date: its contra is a liability.
		self.assert_balances(
			"2026-03-31",
			accrual={RENT: 1000, CREDITORS: -900, tds_account.name: -100},
			cash={RENT: 100, CREDITORS: 0, tds_account.name: -100},
		)
		pay(invoice, "2026-04-10", 900)
		self.assert_balances(
			"2026-04-30", from_date="2026-04-01", accrual={RENT: 0}, cash={RENT: 900, BANK: -900}
		)
		self.assert_invariants("2026-04-30", fully_paid=True)

	def test_cb19_fixed_asset_on_credit(self):
		# A purchase of a fixed asset on credit has no convertible line. Each account stays as posted.
		make_journal_entry(
			"2026-03-01",
			[
				{"account": EQUIPMENT, "debit": 5000},
				{"account": CREDITORS, "credit": 5000, "party_type": "Supplier", "party": SUPPLIER},
			],
		)
		balances = {EQUIPMENT: 5000, CREDITORS: -5000}
		self.assert_balances("2026-03-31", accrual=balances, cash=balances)
		self.assertEqual(self.adjustments("2026-03-31"), [])
		self.assertEqual(self.exception_reasons(), {})
