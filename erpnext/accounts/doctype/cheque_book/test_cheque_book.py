# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import call, patch

import frappe

from erpnext.accounts.doctype.cheque_book.cheque_book import (
	cancel_cheque_payment,
	get_next_cheque,
	get_next_cheque_book_no,
	is_cheque_payment,
)
from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry
from erpnext.tests.utils import ERPNextTestSuite

BANK_LEDGER = "_Test Cheque Bank - _TC"


class TestChequeBook(ERPNextTestSuite):
	def setUp(self):
		if not frappe.db.exists("Mode of Payment", "Cheque"):
			frappe.get_doc(
				{"doctype": "Mode of Payment", "mode_of_payment": "Cheque", "type": "Bank"}
			).insert()
		self.bank_account = make_company_bank_account()
		self.book = make_cheque_book(self.bank_account, "CB-1", "000101", "000105")

	def make_cheque_payment(self, reference_no=None, submit=True, cheque_book=None, **args):
		args.setdefault("paid_from", BANK_LEDGER)
		pe = create_payment_entry(**args)
		pe.mode_of_payment = "Cheque"
		pe.cheque_book = cheque_book or (self.book.name if reference_no else None)
		pe.reference_no = reference_no
		pe.save()
		if submit:
			pe.submit()
		return pe

	def test_invalid_ranges_are_rejected(self):
		for index, (start, end, no_of_cheques) in enumerate(
			(
				("110", "100", None),
				("10a", "120", None),
				("0100", "120", None),
				("123456789012345678901", "123456789012345678909", None),
				(None, None, 5),
				("000201", None, 0),
				(None, "000005", 10),
			)
		):
			with self.subTest(start=start, end=end, no_of_cheques=no_of_cheques):
				self.assertRaises(
					frappe.ValidationError,
					make_cheque_book,
					self.bank_account,
					f"BAD-{index}",
					start,
					end,
					no_of_cheques=no_of_cheques,
				)

	def test_third_range_value_is_calculated(self):
		book = make_cheque_book(self.bank_account, "CB-A", "000201", "000205")
		self.assertEqual(book.no_of_cheques, 5)

		book = make_cheque_book(self.bank_account, "CB-B", "000301", None, no_of_cheques=25)
		self.assertEqual(book.cheque_end_no, "000325")

		book = make_cheque_book(self.bank_account, "CB-C", None, "000425", no_of_cheques=25)
		self.assertEqual(book.cheque_start_no, "000401")

	def test_twenty_digit_cheque_numbers_are_exact(self):
		book = make_cheque_book(self.bank_account, "CB-20", "12345678901234567890", "12345678901234567895")
		self.assertEqual(book.no_of_cheques, 6)
		self.assertEqual(get_next_cheque(BANK_LEDGER, book.name)["cheque_no"], "12345678901234567890")
		self.make_cheque_payment("12345678901234567890", cheque_book=book.name)
		book.reload()
		self.assertEqual(book.next_cheque_no, "12345678901234567891")

	def test_derived_twenty_one_digit_end_is_rejected_clearly(self):
		with self.assertRaisesRegex(frappe.ValidationError, "at most 20 digits"):
			make_cheque_book(self.bank_account, "CB-OVERFLOW", "99999999999999999999", None, no_of_cheques=2)

	def test_cheque_count_must_fit_int_field(self):
		with self.assertRaisesRegex(frappe.ValidationError, "cannot exceed"):
			make_cheque_book(self.bank_account, "CB-TOO-MANY", "00000000000000000001", "00000000003000000000")

	def test_bookmark_can_pass_twenty_digit_end(self):
		book = make_cheque_book(self.bank_account, "CB-END", "99999999999999999999", "99999999999999999999")
		self.make_cheque_payment("99999999999999999999", cheque_book=book.name)
		book.reload()
		self.assertEqual((book.next_cheque_no, book.status), ("100000000000000000000", "Finished"))

	def test_overlapping_range_is_rejected(self):
		self.assertRaises(
			frappe.ValidationError, make_cheque_book, self.bank_account, "CB-2", "000105", "000110"
		)
		self.assertRaises(frappe.ValidationError, make_cheque_book, self.bank_account, "CB-2", "101", "105")
		make_cheque_book(self.bank_account, "CB-3", "000106", "000110")

	def test_next_cheque_book_no_is_suggested(self):
		# the only book of this account is named CB-1, so there is no number to follow
		self.assertEqual(get_next_cheque_book_no(self.bank_account), "01")

		make_cheque_book(self.bank_account, "07", "000201", "000205")
		self.assertEqual(get_next_cheque_book_no(self.bank_account), "08")

		# the highest number wins, not the latest book, and a cancelled one still counts
		book = make_cheque_book(self.bank_account, "09", "000301", "000305")
		make_cheque_book(self.bank_account, "08", "000401", "000405")
		book.cancel()
		self.assertEqual(get_next_cheque_book_no(self.bank_account), "10")

	def test_duplicate_cheque_book_no_is_rejected(self):
		# the name is {bank_account}-{cheque_book_no}, so a duplicate cannot be inserted
		self.assertRaises(
			frappe.DuplicateEntryError, make_cheque_book, self.bank_account, "CB-1", "000201", "000205"
		)

	def test_disabled_book_is_not_used(self):
		self.book.db_set("status", "Disabled")
		self.assertEqual(get_next_cheque(BANK_LEDGER), {})
		self.assertRaises(frappe.ValidationError, self.make_cheque_payment, "000101")

	def test_disabled_bank_account_blocks_book_creation(self):
		frappe.db.set_value("Bank Account", self.bank_account, "disabled", 1)
		with self.assertRaisesRegex(frappe.ValidationError, "disabled"):
			make_cheque_book(self.bank_account, "CB-DISABLED", "000201", "000205")

	def test_disabled_bank_account_blocks_cheque_use_without_changing_book_status(self):
		frappe.db.set_value("Bank Account", self.bank_account, "disabled", 1)
		self.assertEqual(get_next_cheque(BANK_LEDGER), {})
		self.assertEqual(get_next_cheque(BANK_LEDGER, self.book.name), {})
		with self.assertRaisesRegex(frappe.ValidationError, "disabled"):
			self.make_cheque_payment("000101")
		self.book.reload()
		self.assertEqual(self.book.status, "Submitted")

		frappe.db.set_value("Bank Account", self.bank_account, "disabled", 0)
		self.assertEqual(get_next_cheque(BANK_LEDGER)["cheque_no"], "000101")
		self.make_cheque_payment("000101")

	def test_disabling_bank_account_before_payment_submission_blocks_draft(self):
		payment = self.make_cheque_payment("000101", submit=False)
		frappe.db.set_value("Bank Account", self.bank_account, "disabled", 1)
		with self.assertRaisesRegex(frappe.ValidationError, "disabled"):
			payment.submit()

		frappe.db.set_value("Bank Account", self.bank_account, "disabled", 0)
		frappe.get_doc("Payment Entry", payment.name).submit()

	def test_book_cannot_be_used_if_bank_account_is_no_longer_a_company_account(self):
		frappe.db.set_value("Bank Account", self.bank_account, "is_company_account", 0)
		self.assertEqual(get_next_cheque(BANK_LEDGER), {})
		with self.assertRaisesRegex(frappe.ValidationError, "not a Company Account"):
			self.make_cheque_payment("000101")

	def test_manual_book_status_is_preserved_while_bank_account_is_disabled(self):
		frappe.db.set_value("Bank Account", self.bank_account, "disabled", 1)
		self.book.status = "Disabled"
		self.book.save()
		frappe.db.set_value("Bank Account", self.bank_account, "disabled", 0)
		self.book.reload()
		self.assertEqual(self.book.status, "Disabled")
		self.assertEqual(get_next_cheque(BANK_LEDGER), {})

	def test_draft_book_is_not_used(self):
		book = make_cheque_book(self.bank_account, "CB-DRAFT", "000200", "000210", submit=False)
		self.assertEqual(book.status, "Draft")
		self.assertRaises(frappe.ValidationError, self.make_cheque_payment, "000200", cheque_book=book.name)

	def test_next_cheque_no_starts_at_cheque_start_no(self):
		self.assertEqual(self.book.next_cheque_no, "000101")
		self.assertEqual(get_next_cheque(BANK_LEDGER, include_free=True)["free"], 5)

		self.make_cheque_payment()
		self.assertEqual(get_next_cheque(BANK_LEDGER, include_free=True)["free"], 4)

	def test_submitted_bookmark_cannot_be_changed_with_normal_save(self):
		self.book.next_cheque_no = "000104"
		with self.assertRaises(frappe.ValidationError):
			self.book.save()

	def test_free_count_uses_all_numbers_not_just_bookmark(self):
		self.make_cheque_payment("000104")
		cancelled = cancel_cheque(self.book.name, "000105")
		self.assertEqual(get_next_cheque(BANK_LEDGER, self.book.name, include_free=True)["free"], 3)

		payment = self.make_cheque_payment("000101")
		payment.cancel()
		self.assertEqual(get_next_cheque(BANK_LEDGER, self.book.name, include_free=True)["free"], 3)

		cancelled.delete()
		self.assertEqual(get_next_cheque(BANK_LEDGER, self.book.name, include_free=True)["free"], 4)

	def test_next_cheque_is_suggested_and_marked_used_on_submit(self):
		pe = self.make_cheque_payment()
		self.assertEqual((pe.cheque_book, pe.reference_no), (self.book.name, "000101"))
		self.book.reload()
		self.assertEqual(self.book.next_cheque_no, "000102")
		self.assertEqual(get_next_cheque(BANK_LEDGER)["cheque_no"], "000102")

	def test_out_of_sequence_cheque_keeps_earlier_numbers_available(self):
		self.make_cheque_payment("000104")
		self.book.reload()
		self.assertEqual((self.book.next_cheque_no, self.book.status), ("000101", "Submitted"))
		self.assertEqual(get_next_cheque(BANK_LEDGER)["cheque_no"], "000101")

		# and the number already used is stepped over when it is reached
		for cheque_no in ("000101", "000102", "000103"):
			self.make_cheque_payment(cheque_no)
		self.book.reload()
		self.assertEqual(self.book.next_cheque_no, "000105")

	def test_cancelling_a_later_cheque_does_not_move_the_next_cheque_no(self):
		self.make_cheque_payment()
		cancel_cheque(self.book.name, "000105")
		self.book.reload()
		self.assertEqual((self.book.next_cheque_no, self.book.status), ("000102", "Submitted"))
		self.assertEqual(get_next_cheque(BANK_LEDGER)["cheque_no"], "000102")

	def test_book_is_finished_when_the_last_cheque_is_used(self):
		cancel_cheque(self.book.name, "000105")
		for cheque_no in ("000101", "000102", "000103", "000104"):
			self.make_cheque_payment(cheque_no)

		self.book.reload()
		self.assertEqual((self.book.next_cheque_no, self.book.status), ("000106", "Finished"))
		self.assertEqual(get_next_cheque(BANK_LEDGER), {})

	def test_book_stays_submitted_when_bookmark_passes_a_freed_cheque(self):
		payment = self.make_cheque_payment("000101")
		payment.cancel()
		for cheque_no in ("000102", "000103", "000104", "000105"):
			self.make_cheque_payment(cheque_no)

		self.book.reload()
		self.assertEqual((self.book.next_cheque_no, self.book.status), ("000106", "Submitted"))
		self.assertEqual(
			get_next_cheque(BANK_LEDGER, include_free=True), {"cheque_book": self.book.name, "free": 1}
		)

		self.make_cheque_payment("000101")
		self.book.reload()
		self.assertEqual(self.book.status, "Finished")

	def test_finished_book_reopens_when_payment_is_cancelled(self):
		payments = [self.make_cheque_payment(no) for no in ("000101", "000102", "000103", "000104", "000105")]
		self.book.reload()
		self.assertEqual(self.book.status, "Finished")

		payments[1].cancel()
		self.book.reload()
		self.assertEqual((self.book.next_cheque_no, self.book.status), ("000102", "Submitted"))
		self.assertEqual(get_next_cheque(BANK_LEDGER)["cheque_no"], "000102")

		payments[0].cancel()
		self.book.reload()
		self.assertEqual(self.book.next_cheque_no, "000102")

	def test_cancelling_payment_with_reason_records_cancelled_cheque(self):
		payment = self.make_cheque_payment("000101")
		cancel_cheque_payment(payment.name, "Spoiled", "Printer jam")

		self.assertEqual(frappe.db.get_value("Payment Entry", payment.name, "docstatus"), 2)
		cancelled = frappe.get_doc("Cancelled Cheque", f"{self.book.name}-000101")
		self.assertEqual(
			(cancelled.payment_entry, cancelled.reason, cancelled.remarks),
			(payment.name, "Spoiled", "Printer jam"),
		)
		self.assertRaises(frappe.ValidationError, self.make_cheque_payment, "000101")

	def test_reason_is_required_for_atomic_cheque_cancellation(self):
		payment = self.make_cheque_payment("000101")
		with self.assertRaises(frappe.ValidationError):
			cancel_cheque_payment(payment.name, "")
		self.assertEqual(frappe.db.get_value("Payment Entry", payment.name, "docstatus"), 1)

	def test_cancelled_cheque_link_blocks_payment_entry_deletion(self):
		payment = self.make_cheque_payment("000101")
		cancel_cheque_payment(payment.name, "Spoiled")

		with self.assertRaises(frappe.LinkExistsError):
			frappe.delete_doc("Payment Entry", payment.name)

	def test_failed_cancelled_cheque_insert_rolls_back_payment_cancellation(self):
		from erpnext.accounts.doctype.cancelled_cheque.cancelled_cheque import CancelledCheque

		payment = self.make_cheque_payment("000101")
		frappe.db.savepoint("cheque_cancellation")
		with patch.object(CancelledCheque, "insert", side_effect=frappe.ValidationError("Insert failed")):
			with self.assertRaisesRegex(frappe.ValidationError, "Insert failed"):
				cancel_cheque_payment(payment.name, "Spoiled")
		frappe.db.rollback(save_point="cheque_cancellation")
		self.assertEqual(frappe.db.get_value("Payment Entry", payment.name, "docstatus"), 1)
		self.assertFalse(frappe.db.exists("Cancelled Cheque", f"{self.book.name}-000101"))

	def test_finished_book_reopens_when_cancelled_cheque_is_deleted(self):
		cancelled = [
			cancel_cheque(self.book.name, no) for no in ("000101", "000102", "000103", "000104", "000105")
		]
		self.book.reload()
		self.assertEqual(self.book.status, "Finished")

		cancelled[2].delete()
		self.book.reload()
		self.assertEqual((self.book.next_cheque_no, self.book.status), ("000103", "Submitted"))
		self.assertEqual(get_next_cheque(BANK_LEDGER)["cheque_no"], "000103")

	def test_deleting_direct_cancelled_cheque_can_make_book_deletable(self):
		book = make_cheque_book(self.bank_account, "CB-ONE", "000201", "000201")
		cancelled = cancel_cheque(book.name, "000201")
		book.reload()
		self.assertEqual(book.status, "Finished")

		cancelled.delete()
		book.reload()
		self.assertEqual((book.next_cheque_no, book.status), ("000201", "Submitted"))
		book.cancel()
		book.delete()
		self.assertFalse(frappe.db.exists("Cheque Book", book.name))

	def test_next_book_is_used_when_one_is_finished(self):
		make_cheque_book(self.bank_account, "CB-NEXT", "000300", "000300")
		for cheque_no in ("000101", "000102", "000103", "000104", "000105"):
			cancel_cheque(self.book.name, cheque_no)

		self.book.reload()
		self.assertEqual(self.book.status, "Finished")

		pe = self.make_cheque_payment()
		self.assertEqual((pe.cheque_book, pe.reference_no), (f"{self.bank_account}-CB-NEXT", "000300"))

	def test_finished_book_still_accepts_an_amended_payment(self):
		book = make_cheque_book(self.bank_account, "CB-ONE", "000201", "000201")
		pe = self.make_cheque_payment("000201", cheque_book=book.name)
		book.reload()
		self.assertEqual(book.status, "Finished")

		pe.cancel()
		amended = frappe.copy_doc(pe)
		amended.docstatus = 0
		amended.amended_from = pe.name
		amended.submit()
		self.assertEqual(amended.reference_no, "000201")

		book.reload()
		self.assertEqual((book.next_cheque_no, book.status), ("000202", "Finished"))

	def test_typed_number_is_padded(self):
		pe = self.make_cheque_payment("103")
		self.assertEqual(pe.reference_no, "000103")

	def test_extra_leading_zeros_are_normalized_for_payment(self):
		book = make_cheque_book(self.bank_account, "CB-SHORT", "1", "5")
		pe = self.make_cheque_payment("001", cheque_book=book.name)
		self.assertEqual(pe.reference_no, "1")
		self.assertRaises(frappe.ValidationError, self.make_cheque_payment, "01", cheque_book=book.name)

	def test_two_drafts_take_the_same_number_and_the_first_submit_wins(self):
		draft = self.make_cheque_payment(submit=False)
		second = self.make_cheque_payment(submit=False)
		self.assertEqual((draft.reference_no, second.reference_no), ("000101", "000101"))

		draft.submit()
		self.assertRaises(frappe.ValidationError, second.submit)

	def test_used_out_of_range_and_cancelled_numbers_are_rejected(self):
		self.make_cheque_payment("000101")
		cancel_cheque(self.book.name, "000102")
		for cheque_no in ("000101", "000102", "000999"):
			with self.subTest(cheque_no=cheque_no):
				self.assertRaises(frappe.ValidationError, self.make_cheque_payment, cheque_no)

	def test_book_must_belong_to_account_paid_from(self):
		self.assertRaises(
			frappe.ValidationError,
			self.make_cheque_payment,
			"000101",
			paid_from="_Test Bank - _TC",
			cheque_book=self.book.name,
		)

	def test_cheque_book_is_required_when_account_has_books(self):
		pe = create_payment_entry(paid_from=BANK_LEDGER)
		pe.mode_of_payment = "Cheque"
		pe.reference_no = "ANY"
		self.assertRaises(frappe.ValidationError, pe.save)

	def test_non_cheque_payments_are_not_checked(self):
		pe = create_payment_entry(paid_from=BANK_LEDGER)
		pe.reference_no = "NEFT-1"
		pe.cheque_book = self.book.name
		pe.save()
		self.assertIsNone(pe.cheque_book)

		receipt = create_payment_entry(
			payment_type="Receive",
			party_type="Customer",
			party="_Test Customer",
			paid_from="Debtors - _TC",
			paid_to=BANK_LEDGER,
		)
		receipt.mode_of_payment = "Cheque"
		receipt.reference_no = "CUSTOMER-CHEQUE"
		receipt.save()
		self.assertIsNone(receipt.cheque_book)

	def test_only_installed_cheque_and_check_modes_are_recognized(self):
		from erpnext.setup.setup_wizard.operations.install_fixtures import get_preset_records

		self.assertIn(
			"Cheque",
			[record.get("mode_of_payment") for record in get_preset_records("India")],
		)
		for mode in ("Cheque", "Check"):
			self.assertTrue(is_cheque_payment(frappe._dict(payment_type="Pay", mode_of_payment=mode)))
		self.assertFalse(is_cheque_payment(frappe._dict(payment_type="Pay", mode_of_payment="Chèque")))

	def test_cancelled_payment_is_not_suggested_again_but_can_be_reused(self):
		pe = self.make_cheque_payment("000101")
		pe.cancel()
		self.assertEqual(get_next_cheque(BANK_LEDGER)["cheque_no"], "000102")

		# the number is free again, so amending keeps the same cheque
		amended = frappe.copy_doc(pe)
		amended.docstatus = 0
		amended.amended_from = pe.name
		amended.submit()
		self.assertEqual(amended.reference_no, "000101")

	def test_cheque_used_in_submitted_payment_cannot_be_cancelled(self):
		self.make_cheque_payment("000101")
		self.assertRaises(frappe.ValidationError, cancel_cheque, self.book.name, "000101")

	def test_cancelled_cheque_reads_current_usage_under_book_lock(self):
		original_get_value = frappe.db.get_value
		with patch.object(frappe, "get_doc", wraps=frappe.get_doc) as get_doc:

			def check_usage(*args, **kwargs):
				if (
					args
					and args[0] == "Payment Entry"
					and isinstance(args[1], dict)
					and args[1].get("cheque_book") == self.book.name
				):
					self.assertIn(
						call("Cheque Book", self.book.name, for_update=True), get_doc.call_args_list
					)
					self.assertTrue(kwargs.get("for_update"))
				if args and args[0] == "Cancelled Cheque" and args[1] == f"{self.book.name}-000102":
					self.assertTrue(kwargs.get("for_update"))
				return original_get_value(*args, **kwargs)

			with patch.object(frappe.db, "get_value", side_effect=check_usage):
				cancel_cheque(self.book.name, "000101")

	def test_payment_submission_reads_current_cheque_usage(self):
		original_get_value = frappe.db.get_value
		with patch.object(frappe, "get_doc", wraps=frappe.get_doc) as get_doc:

			def check_usage(*args, **kwargs):
				if args[:3] == ("Cancelled Cheque", f"{self.book.name}-000101", "reason") and kwargs.get(
					"for_update"
				):
					self.assertIn(
						call("Cheque Book", self.book.name, for_update=True), get_doc.call_args_list
					)
				return original_get_value(*args, **kwargs)

			with patch.object(frappe.db, "get_value", side_effect=check_usage) as get_value:
				payment = self.make_cheque_payment("000101")

		self.assertIn(call("Cheque Book", self.book.name, for_update=True), get_doc.call_args_list)
		self.assertIn(
			call("Cancelled Cheque", f"{self.book.name}-000101", "reason", for_update=True),
			get_value.call_args_list,
		)
		self.assertIn(
			call(
				"Payment Entry",
				{
					"cheque_book": self.book.name,
					"reference_no": "000101",
					"name": ("!=", payment.name),
					"docstatus": 1,
				},
				for_update=True,
			),
			get_value.call_args_list,
		)

	def test_duplicate_cancelled_cheque_is_rejected(self):
		cancel_cheque(self.book.name, "102")
		self.assertTrue(frappe.db.exists("Cancelled Cheque", f"{self.book.name}-000102"))
		self.assertRaises(frappe.DuplicateEntryError, cancel_cheque, self.book.name, "000102")

	def test_extra_leading_zeros_are_normalized_for_cancelled_cheque(self):
		book = make_cheque_book(self.bank_account, "CB-SHORT", "1", "5")
		cancelled = cancel_cheque(book.name, "002")
		self.assertEqual(cancelled.cheque_no, "2")
		self.assertRaises(frappe.DuplicateEntryError, cancel_cheque, book.name, "02")
		self.assertRaises(frappe.ValidationError, self.make_cheque_payment, "0002", cheque_book=book.name)

	def test_cancelled_cheque_can_link_matching_cancelled_payment(self):
		pe = self.make_cheque_payment("000101")
		pe.cancel()

		cancelled = cancel_cheque(self.book.name, "101", payment_entry=pe.name)
		self.assertEqual((cancelled.cheque_no, cancelled.payment_entry), ("000101", pe.name))

	def test_cancelled_cheque_link_ignores_leading_zero_differences(self):
		pe = self.make_cheque_payment("000101")
		pe.cancel()
		pe.db_set("reference_no", "101")

		cancelled = cancel_cheque(self.book.name, "000101", payment_entry=pe.name)
		self.assertEqual(cancelled.payment_entry, pe.name)

	def test_cancelled_cheque_cannot_link_payment_for_another_number(self):
		pe = self.make_cheque_payment("000101")
		pe.cancel()

		with self.assertRaisesRegex(frappe.ValidationError, "must be cancelled and use"):
			cancel_cheque(self.book.name, "000102", payment_entry=pe.name)

	def test_cancelled_cheque_cannot_link_payment_from_another_book(self):
		other_account = (
			frappe.get_doc(
				{
					"doctype": "Account",
					"account_type": "Bank",
					"account_name": "_Test Other Cheque Bank",
					"company": "_Test Company",
					"parent_account": "Bank Accounts - _TC",
				}
			)
			.insert()
			.name
		)
		other_bank_account = (
			frappe.get_doc(
				{
					"doctype": "Bank Account",
					"account_name": "_Test Other Cheque Account",
					"bank": "_Test Cheque Bank",
					"is_company_account": 1,
					"company": "_Test Company",
					"account": other_account,
				}
			)
			.insert()
			.name
		)
		other_book = make_cheque_book(other_bank_account, "CB-OTHER", "000101", "000105")
		pe = self.make_cheque_payment("000101", cheque_book=other_book.name, paid_from=other_account)
		pe.cancel()

		with self.assertRaisesRegex(frappe.ValidationError, "must be cancelled and use"):
			cancel_cheque(self.book.name, "000101", payment_entry=pe.name)

	def test_cancelled_cheque_cannot_link_submitted_payment(self):
		pe = self.make_cheque_payment("000101")

		with self.assertRaisesRegex(frappe.ValidationError, "must be cancelled and use"):
			cancel_cheque(self.book.name, "000102", payment_entry=pe.name)

	def test_cancelled_cheque_revalidates_payment_link_on_edit(self):
		pe = self.make_cheque_payment("000101")
		pe.cancel()
		cancelled = cancel_cheque(self.book.name, "000102")
		cancelled.payment_entry = pe.name

		with self.assertRaisesRegex(frappe.ValidationError, "must be cancelled and use"):
			cancelled.save()

	def test_book_with_issued_cheque_cannot_be_cancelled(self):
		self.make_cheque_payment("000101")
		self.book.reload()
		self.assertRaises(frappe.LinkExistsError, self.book.cancel)

	def test_book_with_cancelled_cheque_cannot_be_cancelled(self):
		cancel_cheque(self.book.name, "000102")
		self.book.reload()
		self.assertRaises(frappe.ValidationError, self.book.cancel)

	def test_unused_book_can_be_cancelled_and_amended(self):
		self.book.cancel()
		self.assertEqual(self.book.status, "Cancelled")

		amended = frappe.copy_doc(self.book)
		amended.amended_from = self.book.name
		amended.cheque_end_no = "000110"
		amended.submit()
		self.assertEqual(get_next_cheque(BANK_LEDGER)["cheque_book"], amended.name)

	def test_amended_book_is_active_and_keeps_its_place(self):
		self.book.db_set("status", "Disabled")
		self.book.cancel()

		# the Amend button drops no_copy fields, so the status starts again as Active
		amended = frappe.copy_doc(self.book, ignore_no_copy=False)
		amended.docstatus = 0
		amended.amended_from = self.book.name
		amended.cheque_end_no = "000110"
		amended.submit()
		self.assertEqual((amended.status, amended.next_cheque_no), ("Submitted", "000101"))


def make_company_bank_account():
	if not frappe.db.exists("Account", BANK_LEDGER):
		frappe.get_doc(
			{
				"doctype": "Account",
				"account_type": "Bank",
				"account_name": "_Test Cheque Bank",
				"company": "_Test Company",
				"parent_account": "Bank Accounts - _TC",
			}
		).insert()

	if not frappe.db.exists("Bank", "_Test Cheque Bank"):
		frappe.get_doc({"doctype": "Bank", "bank_name": "_Test Cheque Bank"}).insert()

	return frappe.db.get_value("Bank Account", {"account": BANK_LEDGER}) or (
		frappe.get_doc(
			{
				"doctype": "Bank Account",
				"account_name": "_Test Cheque Account",
				"bank": "_Test Cheque Bank",
				"is_company_account": 1,
				"company": "_Test Company",
				"account": BANK_LEDGER,
			}
		)
		.insert()
		.name
	)


def make_cheque_book(bank_account, cheque_book_no, start, end, submit=True, no_of_cheques=None):
	book = frappe.get_doc(
		{
			"doctype": "Cheque Book",
			"bank_account": bank_account,
			"cheque_book_no": cheque_book_no,
			"cheque_start_no": start,
			"cheque_end_no": end,
			"no_of_cheques": no_of_cheques,
		}
	).insert()
	if submit:
		book.submit()
	return book


def cancel_cheque(cheque_book, cheque_no, payment_entry=None):
	return frappe.get_doc(
		{
			"doctype": "Cancelled Cheque",
			"cheque_book": cheque_book,
			"cheque_no": cheque_no,
			"reason": "Spoiled",
			"payment_entry": payment_entry,
		}
	).insert()
