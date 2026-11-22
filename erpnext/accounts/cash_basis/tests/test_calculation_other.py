# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Scenarios CB-16, CB-17, CB-18, CB-22: currency, stock, opening. CB-21 is in test_calculation_deferred."""

import frappe

from erpnext.accounts.cash_basis.tests.cash_basis_case import CashBasisTestCase
from erpnext.accounts.cash_basis.tests.fixtures import EUR_CUSTOMER, STOCK_ITEM, US_COMPANY, acc
from erpnext.accounts.cash_basis.tests.vouchers import BANK, MAIN_CC, line, make_sales_invoice, pay, save

SALES = acc("Sales")
DEBTORS = acc("Debtors")
DEBTORS_EUR = acc("Debtors EUR")
EXCHANGE = acc("Exchange Gain")
UNREALIZED = acc("Unrealized Exchange Gain/Loss")
STOCK = acc("Stock In Hand")
COGS = acc("Cost of Goods Sold")
OPENING = acc("Temporary Opening")


class TestCashBasisOther(CashBasisTestCase):
	def make_eur_invoice(self):
		return make_sales_invoice(
			"2026-03-01",
			[line(100)],
			customer=EUR_CUSTOMER,
			currency="EUR",
			conversion_rate=1.10,
			debit_to=DEBTORS_EUR,
			party_account_currency="EUR",
			ignore_pricing_rule=1,
		)

	def test_cb16_foreign_currency_payment_at_another_rate(self):
		invoice = self.make_eur_invoice()
		payment = frappe.new_doc("Payment Entry")
		payment.update(
			{
				"company": US_COMPANY,
				"payment_type": "Receive",
				"party_type": "Customer",
				"party": EUR_CUSTOMER,
				"posting_date": "2026-04-10",
				"paid_from": DEBTORS_EUR,
				"paid_from_account_currency": "EUR",
				"paid_to": BANK,
				"paid_to_account_currency": "USD",
				"paid_amount": 100,
				"source_exchange_rate": 1.20,
				"received_amount": 120,
				"target_exchange_rate": 1,
				"reference_no": "FX1",
				"reference_date": "2026-04-10",
			}
		)
		payment.append(
			"references",
			{"reference_doctype": "Sales Invoice", "reference_name": invoice.name, "allocated_amount": 100},
		)
		save(payment, submit=True)
		# The ratio is in EUR: the payment of 100 EUR settles all of the invoice. The gain is realised.
		self.assert_balances(
			"2026-04-30",
			from_date="2026-04-01",
			accrual={SALES: 0, EXCHANGE: -10, BANK: 120},
			cash={SALES: -110, EXCHANGE: -10, BANK: 120},
		)
		self.assert_balances("2026-04-30", accrual={DEBTORS_EUR: 0}, cash={DEBTORS_EUR: 0, SALES: -110})

	def test_cb17_revaluation_of_open_foreign_currency_invoice(self):
		frappe.db.set_value("Company", US_COMPANY, "unrealized_exchange_gain_loss_account", UNREALIZED)
		self.make_eur_invoice()
		revaluation = frappe.new_doc("Exchange Rate Revaluation")
		revaluation.update({"company": US_COMPANY, "posting_date": "2026-03-31"})
		revaluation.extend("accounts", revaluation.get_accounts_data())
		for row in revaluation.accounts:
			row.new_exchange_rate = 1.25
			row.new_balance_in_base_currency = row.new_exchange_rate * row.balance_in_account_currency
			row.gain_loss = row.new_balance_in_base_currency - row.balance_in_base_currency
		revaluation.set_total_gain_loss()
		save(revaluation, submit=True)
		journals = revaluation.make_jv_entries()
		frappe.get_doc("Journal Entry", journals.get("revaluation_jv")).submit()

		# The unrealised gain of 15 on the receivable does not belong on a cash basis.
		self.assert_balances(
			"2026-03-31",
			accrual={SALES: -110, UNREALIZED: -15, DEBTORS_EUR: 125},
			cash={SALES: 0, UNREALIZED: 0, DEBTORS_EUR: 0},
		)

	def test_cb18_stock_item_with_perpetual_inventory(self):
		receipt = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Material Receipt",
				"company": US_COMPANY,
				"posting_date": "2026-01-02",
				"set_posting_time": 1,
				"items": [
					{
						"item_code": STOCK_ITEM,
						"qty": 10,
						"basic_rate": 40,
						"t_warehouse": acc("Stores"),
						"cost_center": MAIN_CC,
						"expense_account": acc("Stock Adjustment"),
					}
				],
			}
		)
		save(receipt, submit=True)
		invoice = make_sales_invoice(
			"2026-03-01", [line(100, item_code=STOCK_ITEM, warehouse=acc("Stores"))], update_stock=1
		)
		pay(invoice, "2026-04-10")
		# Cost of goods sold stays on the delivery date. The income moves to the payment date.
		self.assert_balances(
			"2026-03-31",
			from_date="2026-03-01",
			accrual={SALES: -100, COGS: 40, STOCK: -40},
			cash={SALES: 0, COGS: 40, STOCK: -40},
		)
		self.assert_balances("2026-04-30", from_date="2026-04-01", accrual={SALES: 0}, cash={SALES: -100})

	def test_cb22_opening_invoice(self):
		make_sales_invoice("2026-01-01", [line(100, account=OPENING)], is_opening="Yes")
		# The opening invoice posts to a balance sheet account. It has no convertible line.
		balances = {OPENING: -100, DEBTORS: 100}
		self.assert_balances("2026-01-31", accrual=balances, cash=balances)
		self.assertEqual(self.adjustments("2026-01-31"), [])
		self.assertEqual(self.exception_reasons(), {})
