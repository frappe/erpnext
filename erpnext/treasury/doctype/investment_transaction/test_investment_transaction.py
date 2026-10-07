# Copyright (c) 2026, Aagnya Mistry and contributors
# See license.txt

import frappe
from frappe.utils import nowdate

from erpnext.tests.utils import ERPNextTestSuite
from erpnext.treasury.doctype.investment.test_investment import (
	create_financial_institution,
	create_investment_type,
	make_investment,
)

BANK_ACCOUNT = "_Test Bank - _TC"
INVESTMENT_ACCOUNTS = {
	"investment_account": "Short-term Investments - _TC",
	"accrued_interest_account": "Earnest Money - _TC",
	"interest_income_account": "Interest on Fixed Deposits - _TC",
	"dividend_income_account": "Interest Income - _TC",
	"realised_gain_loss_account": "Gain/Loss on Asset Disposal - _TC",
	"charges_account": "Bank Charges - _TC",
	"tax_withheld_receivable_account": "Prepaid Expenses - _TC",
}


class TestInvestmentTransaction(ERPNextTestSuite):
	def setUp(self):
		create_investment_type("_Test Bank FD", "Deposit")
		create_investment_type("_Test Equity Fund", "Units")
		create_financial_institution("_Test Bank")

	def test_transaction_needs_approved_investment(self):
		investment = make_investment(**INVESTMENT_ACCOUNTS).insert()
		transaction = make_transaction(investment.name, "Purchase", gross_amount=1000)
		self.assertRaises(frappe.ValidationError, transaction.insert)

	def test_purchase_posts_gl(self):
		investment = make_submitted_investment()
		transaction = make_transaction(investment.name, "Purchase", gross_amount=100000, charges=500).submit()

		self.assertEqual(transaction.net_amount, 100500)
		self.assertEqual(
			get_gl_entries(transaction.name),
			{
				"Short-term Investments - _TC": (100000, 0),
				"Bank Charges - _TC": (500, 0),
				BANK_ACCOUNT: (0, 100500),
			},
		)

		investment.reload()
		self.assertEqual(investment.total_cost, 100000)
		self.assertEqual(investment.status, "Active")

	def test_purchase_above_approved_amount_is_blocked(self):
		investment = make_submitted_investment(approved_amount=100000)
		make_transaction(investment.name, "Purchase", gross_amount=60000).submit()

		transaction = make_transaction(investment.name, "Purchase", gross_amount=50000)
		self.assertRaises(frappe.ValidationError, transaction.insert)

	def test_sale_uses_fifo_cost(self):
		investment = make_submitted_investment(investment_type="_Test Equity Fund")
		make_transaction(investment.name, "Purchase", units=100, rate=10).submit()
		make_transaction(investment.name, "Purchase", units=100, rate=12).submit()

		sale = make_transaction(investment.name, "Sale", units=150, rate=15).submit()

		# 100 units at 10 + 50 units at 12
		self.assertEqual(sale.cost_of_units_sold, 1600)
		self.assertEqual(sale.realised_gain_loss, 650)
		self.assertEqual(
			get_gl_entries(sale.name),
			{
				BANK_ACCOUNT: (2250, 0),
				"Short-term Investments - _TC": (0, 1600),
				"Gain/Loss on Asset Disposal - _TC": (0, 650),
			},
		)

		investment.reload()
		self.assertEqual(investment.units_held, 50)
		self.assertEqual(investment.total_cost, 600)
		self.assertEqual(investment.status, "Partially Redeemed")

	def test_cannot_sell_more_units_than_held(self):
		investment = make_submitted_investment(investment_type="_Test Equity Fund")
		make_transaction(investment.name, "Purchase", units=100, rate=10).submit()

		sale = make_transaction(investment.name, "Sale", units=101, rate=10)
		self.assertRaises(frappe.ValidationError, sale.insert)

	def test_cancel_purchase_reverses_gl(self):
		investment = make_submitted_investment()
		transaction = make_transaction(investment.name, "Purchase", gross_amount=100000).submit()

		transaction.cancel()

		self.assertFalse(get_gl_entries(transaction.name))
		investment.reload()
		self.assertEqual(investment.total_cost, 0)

	def test_cannot_cancel_purchase_already_sold(self):
		investment = make_submitted_investment(investment_type="_Test Equity Fund")
		purchase = make_transaction(investment.name, "Purchase", units=100, rate=10).submit()
		make_transaction(investment.name, "Sale", units=40, rate=10).submit()

		self.assertRaises(frappe.ValidationError, purchase.cancel)

	def test_interest_accrual_and_receipt(self):
		investment = make_submitted_investment()
		make_transaction(investment.name, "Purchase", gross_amount=100000).submit()

		accrual = make_accrual_for_today(investment.name, 750)
		self.assertEqual(
			get_gl_entries(accrual.name, "Investment Interest Accrual"),
			{"Earnest Money - _TC": (750, 0), "Interest on Fixed Deposits - _TC": (0, 750)},
		)
		investment.reload()
		self.assertEqual(investment.accrued_interest, 750)

		receipt = make_transaction(investment.name, "Interest Receipt", interest_amount=750, tax_withheld=75)
		receipt.submit()
		self.assertEqual(
			get_gl_entries(receipt.name),
			{BANK_ACCOUNT: (675, 0), "Prepaid Expenses - _TC": (75, 0), "Earnest Money - _TC": (0, 750)},
		)
		investment.reload()
		self.assertEqual(investment.accrued_interest, 0)

	def test_interest_receipt_needs_accrued_interest(self):
		investment = make_submitted_investment()
		make_transaction(investment.name, "Purchase", gross_amount=100000).submit()

		receipt = make_transaction(investment.name, "Interest Receipt", interest_amount=400)
		self.assertRaises(frappe.ValidationError, receipt.insert)

		make_accrual_for_today(investment.name, 400)
		receipt = make_transaction(investment.name, "Interest Receipt", interest_amount=500)
		self.assertRaises(frappe.ValidationError, receipt.insert)

		receipt.interest_amount = 400
		receipt.insert().submit()
		investment.reload()
		self.assertEqual(investment.accrued_interest, 0)

	def test_cannot_cancel_accrual_already_received(self):
		investment = make_submitted_investment()
		make_transaction(investment.name, "Purchase", gross_amount=100000).submit()
		accrual = make_accrual_for_today(investment.name, 400)
		make_transaction(investment.name, "Interest Receipt", interest_amount=400).submit()

		with self.assertRaises(frappe.ValidationError) as error:
			accrual.cancel()

		self.assertIn(
			f"has already been received. Please cancel the Interest Receipt transactions of Investment <strong>{investment.name}</strong> first.",
			str(error.exception),
		)

	def test_gl_voucher_subtype_is_transaction_type(self):
		investment = make_submitted_investment()
		purchase = make_transaction(investment.name, "Purchase", gross_amount=100000).submit()

		self.assertEqual(
			set(frappe.get_all("GL Entry", {"voucher_no": purchase.name}, pluck="voucher_subtype")),
			{"Purchase"},
		)

	def test_opening_uses_temporary_opening_account(self):
		investment = make_submitted_investment()
		opening = make_transaction(investment.name, "Opening", gross_amount=100000).submit()

		self.assertEqual(
			get_gl_entries(opening.name),
			{"Short-term Investments - _TC": (100000, 0), "Temporary Opening - _TC": (0, 100000)},
		)
		self.assertIsNone(opening.cash_account)

	def test_deposit_maturity_marks_investment_matured(self):
		investment = make_submitted_investment()
		make_transaction(investment.name, "Purchase", gross_amount=100000).submit()
		maturity = make_transaction(investment.name, "Maturity", gross_amount=100000).submit()

		self.assertEqual(maturity.realised_gain_loss, 0)
		investment.reload()
		self.assertEqual(investment.total_cost, 0)
		self.assertEqual(investment.status, "Matured")


def make_submitted_investment(**args):
	investment = make_investment(**INVESTMENT_ACCOUNTS)
	investment.update(args)
	return investment.submit()


def make_transaction(investment, transaction_type, **args):
	transaction = frappe.get_doc(
		{
			"doctype": "Investment Transaction",
			"investment": investment,
			"transaction_type": transaction_type,
			"posting_date": nowdate(),
			"cash_account": BANK_ACCOUNT,
		}
	)
	transaction.update(args)
	return transaction


def make_accrual_for_today(investment, interest_amount):
	return make_interest_accrual(investment, nowdate(), nowdate(), interest_amount).submit()


def make_interest_accrual(investment, from_date, to_date, interest_amount, **args):
	accrual = frappe.get_doc(
		{
			"doctype": "Investment Interest Accrual",
			"investment": investment,
			"from_date": from_date,
			"to_date": to_date,
			"posting_date": to_date,
			"interest_amount": interest_amount,
		}
	)
	accrual.update(args)
	return accrual


def get_gl_entries(voucher_no, voucher_type="Investment Transaction"):
	entries = frappe.get_all(
		"GL Entry",
		filters={"voucher_type": voucher_type, "voucher_no": voucher_no, "is_cancelled": 0},
		fields=["account", "debit", "credit"],
	)
	return {entry.account: (entry.debit, entry.credit) for entry in entries}
