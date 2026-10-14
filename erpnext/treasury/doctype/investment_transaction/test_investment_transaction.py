# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.utils import add_days, nowdate

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

	def test_purchase_ignores_hidden_tax_and_penalty(self):
		investment = make_submitted_investment()
		transaction = make_transaction(
			investment.name, "Purchase", gross_amount=100000, tax_withheld=100, penalty_applied=50
		).submit()

		self.assertEqual((transaction.tax_withheld, transaction.penalty_applied), (0, 0))
		self.assertEqual(
			get_gl_entries(transaction.name),
			{"Short-term Investments - _TC": (100000, 0), BANK_ACCOUNT: (0, 100000)},
		)

	def test_opening_ignores_hidden_bought_interest(self):
		investment = make_submitted_investment()
		opening = make_transaction(
			investment.name, "Opening", gross_amount=100000, accrued_interest_in_purchase=2000
		).submit()

		self.assertEqual(opening.accrued_interest_in_purchase, 0)
		# no interest was accrued, so nothing can be received
		receipt = make_transaction(investment.name, "Interest Receipt", interest_amount=2000)
		self.assertRaises(frappe.ValidationError, receipt.insert)

	def test_finance_book_reaches_the_ledger(self):
		for book in ("_Test Treasury Book", "_Test Other Book"):
			if not frappe.db.exists("Finance Book", book):
				frappe.get_doc({"doctype": "Finance Book", "finance_book_name": book}).insert()

		investment = make_submitted_investment(finance_book="_Test Treasury Book")
		# the holding's book is used, whatever the voucher says, so purchases and exits share one book
		purchase = make_transaction(
			investment.name, "Purchase", gross_amount=1000, finance_book="_Test Other Book"
		).submit()

		finance_books = frappe.get_all(
			"GL Entry", filters={"voucher_no": purchase.name}, pluck="finance_book", distinct=True
		)
		self.assertEqual(finance_books, ["_Test Treasury Book"])

	def test_cost_center_must_belong_to_company(self):
		investment = make_submitted_investment()
		other_cost_center = frappe.db.get_value(
			"Cost Center", {"company": ("!=", investment.company), "is_group": 0}, "name"
		)

		purchase = make_transaction(
			investment.name, "Purchase", gross_amount=1000, cost_center=other_cost_center
		)
		self.assertRaises(frappe.ValidationError, purchase.insert)

	def test_purchase_above_approved_amount_is_blocked(self):
		investment = make_submitted_investment(approved_amount=100000)
		make_transaction(investment.name, "Purchase", gross_amount=60000).submit()

		transaction = make_transaction(investment.name, "Purchase", gross_amount=50000)
		self.assertRaises(frappe.ValidationError, transaction.insert)

	def test_approved_amount_leaves_out_bought_interest(self):
		investment = make_submitted_investment(approved_amount=100000)

		# 101000 paid, but only 99000 is the investment itself; 2000 is interest bought with it
		make_transaction(
			investment.name, "Purchase", gross_amount=101000, accrued_interest_in_purchase=2000
		).submit()

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

	def test_last_sale_takes_cost_left_after_rounding(self):
		investment = make_submitted_investment(investment_type="_Test Equity Fund")
		# 0.3 units for 1.00 is 3.333... per unit, so each 0.1 unit sale costs 0.33 after rounding
		make_transaction(investment.name, "Purchase", units=0.3, rate=3.33).submit()
		make_transaction(investment.name, "Sale", units=0.1, rate=4).submit()
		make_transaction(investment.name, "Sale", units=0.1, rate=4).submit()

		last_sale = make_transaction(investment.name, "Sale", units=0.1, rate=4).submit()

		self.assertEqual(last_sale.cost_of_units_sold, 0.34)
		investment.reload()
		self.assertEqual((investment.total_cost, investment.status), (0, "Redeemed"))

	def test_only_submit_locks_the_balance(self):
		investment = make_submitted_investment(investment_type="_Test Equity Fund")
		make_transaction(investment.name, "Purchase", units=100, rate=10).submit()
		sale = make_transaction(investment.name, "Sale", units=40, rate=10)

		with patch.object(frappe.db, "get_values", wraps=frappe.db.get_values) as get_values:
			sale.insert()
			self.assertFalse(any(call.kwargs.get("for_update") for call in get_values.call_args_list))

			sale.submit()
			self.assertTrue(any(call.kwargs.get("for_update") for call in get_values.call_args_list))

	def test_cannot_cancel_sale_a_later_sale_was_costed_after(self):
		investment = make_submitted_investment(investment_type="_Test Equity Fund")
		make_transaction(investment.name, "Purchase", units=100, rate=10).submit()
		make_transaction(investment.name, "Purchase", units=100, rate=12).submit()
		first_sale = make_transaction(investment.name, "Sale", units=50, rate=15).submit()
		# 50 units at 10 + 50 units at 12, after the first sale took 50 at 10
		second_sale = make_transaction(investment.name, "Sale", units=100, rate=15).submit()
		self.assertEqual(second_sale.cost_of_units_sold, 1100)

		self.assertRaises(frappe.ValidationError, first_sale.cancel)
		second_sale.cancel()
		first_sale.reload().cancel()

	def test_cannot_submit_sale_dated_before_a_later_sale(self):
		investment = make_submitted_investment(investment_type="_Test Equity Fund")
		make_transaction(investment.name, "Purchase", units=100, rate=10).submit()
		make_transaction(
			investment.name, "Sale", units=20, rate=15, posting_date=add_days(nowdate(), 5)
		).submit()

		backdated_sale = make_transaction(
			investment.name, "Sale", units=20, rate=15, posting_date=add_days(nowdate(), 1)
		)
		self.assertRaises(frappe.ValidationError, backdated_sale.submit)

	def test_submit_reads_interest_with_locks(self):
		investment = make_submitted_investment()
		make_transaction(investment.name, "Purchase", gross_amount=100000).submit()
		make_interest_accrual(investment.name, nowdate(), nowdate(), 50).submit()
		receipt = make_transaction(investment.name, "Interest Receipt", interest_amount=50).insert()

		with patch.object(frappe.db, "get_value", wraps=frappe.db.get_value) as get_value:
			receipt.submit()

		investment_locks = [
			call
			for call in get_value.call_args_list
			if call.args[0] == "Investment" and call.kwargs.get("for_update")
		]
		self.assertTrue(investment_locks)

	def test_submit_asks_for_retry_if_investment_changed_while_waiting(self):
		investment = make_submitted_investment()
		purchase = make_transaction(investment.name, "Purchase", gross_amount=1000).insert()
		get_value = frappe.db.get_value

		def committed_meanwhile(doctype, name, fieldname, *args, **kwargs):
			# the locked read sees what another entry committed while this one waited for the lock
			if doctype == "Investment" and kwargs.get("for_update"):
				return add_days(get_value(doctype, name, fieldname), 1)
			return get_value(doctype, name, fieldname, *args, **kwargs)

		with patch.object(frappe.db, "get_value", side_effect=committed_meanwhile):
			self.assertRaises(frappe.TimestampMismatchError, purchase.submit)

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

	def test_cannot_cancel_purchase_whose_cost_a_sale_used(self):
		investment = make_submitted_investment(investment_type="_Test Equity Fund")
		first = make_transaction(investment.name, "Purchase", units=100, rate=10).submit()
		make_transaction(investment.name, "Purchase", units=100, rate=12).submit()
		make_transaction(investment.name, "Sale", units=100, rate=15).submit()

		# the second purchase still covers the units, but the sale took the first one's cost
		self.assertRaises(frappe.ValidationError, first.cancel)

	def test_cannot_backdate_purchase_before_a_sale(self):
		investment = make_submitted_investment(investment_type="_Test Equity Fund")
		make_transaction(investment.name, "Purchase", units=100, rate=10).submit()
		make_transaction(
			investment.name, "Sale", posting_date=add_days(nowdate(), 2), units=50, rate=15
		).submit()

		purchase = make_transaction(
			investment.name, "Purchase", posting_date=add_days(nowdate(), 1), units=100, rate=8
		)
		self.assertRaises(frappe.ValidationError, purchase.submit)

	def test_cannot_sell_units_bought_later(self):
		investment = make_submitted_investment(investment_type="_Test Equity Fund")
		make_transaction(investment.name, "Purchase", units=100, rate=10).submit()
		make_transaction(
			investment.name, "Purchase", posting_date=add_days(nowdate(), 5), units=100, rate=12
		).submit()

		sale = make_transaction(
			investment.name, "Sale", posting_date=add_days(nowdate(), 2), units=150, rate=15
		)
		self.assertRaises(frappe.ValidationError, sale.insert)

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
