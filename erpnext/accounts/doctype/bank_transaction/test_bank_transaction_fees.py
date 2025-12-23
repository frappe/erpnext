# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestBankTransactionFees(FrappeTestCase):
	def test_included_fee_throws(self):
		"""A fee that's part of a withdrawal cannot be bigger than the
		withdrawal itself."""
		bt = frappe.new_doc("Bank Transaction")
		bt.withdrawal = 100
		bt.included_fee = 101

		self.assertRaises(frappe.ValidationError, bt.validate_included_fee)

	def test_included_fee_allows_equal(self):
		"""A fee that's part of a withdrawal may be equal to the withdrawal
		amount (only the fee was deducted from the account)."""
		bt = frappe.new_doc("Bank Transaction")
		bt.withdrawal = 100
		bt.included_fee = 100

		bt.validate_included_fee()

	def test_included_fee_allows_for_deposit(self):
		"""For deposits, a fee may be recorded separately without limiting the
		received amount."""
		bt = frappe.new_doc("Bank Transaction")
		bt.deposit = 10
		bt.included_fee = 999

		bt.validate_included_fee()

	def test_excluded_fee_noop_when_zero(self):
		"""When there is no excluded fee to apply, the amounts should remain
		unchanged."""
		bt = frappe.new_doc("Bank Transaction")
		bt.deposit = 100
		bt.withdrawal = 0
		bt.included_fee = 5
		bt.excluded_fee = 0

		bt.handle_excluded_fee()

		self.assertEqual(bt.deposit, 100)
		self.assertEqual(bt.withdrawal, 0)
		self.assertEqual(bt.included_fee, 5)
		self.assertEqual(bt.excluded_fee, 0)

	def test_excluded_fee_throws_when_exceeds_deposit(self):
		"""A fee deducted from an incoming payment must not exceed the incoming
		amount (else it would be a withdrawal, a conversion we don't support)."""
		bt = frappe.new_doc("Bank Transaction")
		bt.deposit = 10
		bt.excluded_fee = 11

		self.assertRaises(frappe.ValidationError, bt.handle_excluded_fee)

	def test_excluded_fee_throws_when_both_deposit_and_withdrawal_are_set(self):
		"""A transaction must be either incoming or outgoing when applying a
		fee, not both."""
		bt = frappe.new_doc("Bank Transaction")
		bt.deposit = 10
		bt.withdrawal = 10
		bt.excluded_fee = 1

		self.assertRaises(frappe.ValidationError, bt.handle_excluded_fee)

	def test_excluded_fee_deducts_from_deposit(self):
		"""When a fee is deducted from an incoming payment, the net received
		amount decreases and the fee is tracked as included."""
		bt = frappe.new_doc("Bank Transaction")
		bt.deposit = 100
		bt.withdrawal = 0
		bt.included_fee = 2
		bt.excluded_fee = 5

		bt.handle_excluded_fee()

		self.assertEqual(bt.deposit, 95)
		self.assertEqual(bt.withdrawal, 0)
		self.assertEqual(bt.included_fee, 7)
		self.assertEqual(bt.excluded_fee, 0)

	def test_excluded_fee_can_reduce_an_incoming_payment_to_zero(self):
		"""A separately-deducted fee may reduce an incoming payment to zero,
		while still tracking the fee."""
		bt = frappe.new_doc("Bank Transaction")
		bt.deposit = 5
		bt.withdrawal = 0
		bt.included_fee = 0
		bt.excluded_fee = 5

		bt.handle_excluded_fee()

		self.assertEqual(bt.deposit, 0)
		self.assertEqual(bt.withdrawal, 0)
		self.assertEqual(bt.included_fee, 5)
		self.assertEqual(bt.excluded_fee, 0)

	def test_excluded_fee_increases_outgoing_payment(self):
		"""When a separately-deducted fee is provided for an outgoing payment,
		the total money leaving increases and the fee is tracked."""
		bt = frappe.new_doc("Bank Transaction")
		bt.deposit = 0
		bt.withdrawal = 100
		bt.included_fee = 2
		bt.excluded_fee = 5

		bt.handle_excluded_fee()

		self.assertEqual(bt.deposit, 0)
		self.assertEqual(bt.withdrawal, 105)
		self.assertEqual(bt.included_fee, 7)
		self.assertEqual(bt.excluded_fee, 0)

	def test_excluded_fee_turns_zero_amount_into_withdrawal(self):
		"""If only an excluded fee is provided, it should be treated as an
		outgoing payment and the fee is then tracked as included."""
		bt = frappe.new_doc("Bank Transaction")
		bt.deposit = 0
		bt.withdrawal = 0
		bt.included_fee = 0
		bt.excluded_fee = 5

		bt.handle_excluded_fee()

		self.assertEqual(bt.deposit, 0)
		self.assertEqual(bt.withdrawal, 5)
		self.assertEqual(bt.included_fee, 5)
		self.assertEqual(bt.excluded_fee, 0)
