# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from unittest.mock import patch

import frappe

from erpnext.accounts.doctype.cheque_book.cheque_book import get_occupied_cheque_nos, validate_cheque
from erpnext.accounts.doctype.cheque_book.test_cheque_book import (
	make_cheque_book,
	make_company_bank_account,
)
from erpnext.accounts.doctype.cheque_usage.cheque_usage import get_cheque_usage
from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry
from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry
from erpnext.tests.utils import ERPNextTestSuite

test_dependencies = ["Payment Entry"]


class TestChequeUsageConcurrency(ERPNextTestSuite):
	def setUp(self):
		if frappe.db.db_type != "mariadb":
			self.skipTest("These tests exercise MariaDB locking reads and REPEATABLE READ")
		self.site, self.sites_path = frappe.local.site, frappe.local.sites_path
		if not frappe.db.exists("Mode of Payment", "Cheque"):
			frappe.get_doc(
				{"doctype": "Mode of Payment", "mode_of_payment": "Cheque", "type": "Bank"}
			).insert()
		suffix = frappe.generate_hash(length=8)
		self.bank_account = make_company_bank_account(
			f"_Test Concurrent Cheque {suffix}", f"_Test Concurrent Cheque {suffix}"
		)
		self.book = make_cheque_book(self.bank_account, "CONCURRENT", "000101", "000151")
		# Workers need committed fixtures. Cleanup removes only this test's unique book/account.
		frappe.db.commit()
		self.addCleanup(self.clean_up_committed_records)

	def clean_up_committed_records(self):
		frappe.db.rollback()
		for name in frappe.get_all("Payment Entry", filters={"cheque_book": self.book.name}, pluck="name"):
			payment = frappe.get_doc("Payment Entry", name)
			if payment.docstatus == 1:
				payment.cancel()
			# Remove ledger rows belonging only to these committed test payments.
			for doctype in ("GL Entry", "Payment Ledger Entry"):
				frappe.db.delete(doctype, {"voucher_type": "Payment Entry", "voucher_no": name})
			payment.delete()
		book = frappe.get_doc("Cheque Book", self.book.name)
		book.cancel()
		book.delete()
		frappe.delete_doc("Bank Account", self.bank_account)
		frappe.delete_doc("Account", self.book.account)
		frappe.db.commit()

	def make_payment(self, cheque_no, *, submit=False):
		payment = create_payment_entry(paid_from=self.book.account)
		payment.update(
			{"mode_of_payment": "Cheque", "cheque_book": self.book.name, "reference_no": cheque_no}
		)
		payment.save()
		if submit:
			payment.submit()
		return payment

	def run_transaction(self, action, *, committed=None):
		frappe.init(self.site, sites_path=self.sites_path)
		frappe.connect()
		try:
			frappe.db.sql("SET SESSION innodb_lock_wait_timeout = 5")
			for attempt in range(3):
				frappe.flags.cheque_test_attempt = attempt
				try:
					result = action()
					frappe.db.commit()
					if committed:
						committed.set()
					return result
				except frappe.QueryDeadlockError as error:
					# MariaDB's snapshot-isolation conflict needs a whole-transaction retry.
					# An actual circular deadlock (1213) must fail these regression tests.
					if error.__cause__.args[0] != 1020 or attempt == 2:
						raise
					frappe.db.rollback()
					frappe.local.request_cache.clear()
		finally:
			frappe.db.rollback()
			frappe.destroy()

	def test_submission_does_not_wait_for_a_higher_payment_being_cancelled(self):
		later = self.make_payment("000150", submit=True)
		next_payment = self.make_payment("000101")
		frappe.db.commit()
		book_locked, payment_locked, allow_cancel = Event(), Event(), Event()
		original_before_cancel = PaymentEntry.before_cancel

		def validate(payment):
			validate_cheque(payment)
			if not frappe.flags.cheque_test_attempt:
				book_locked.set()
				self.assertTrue(payment_locked.wait(10))
				allow_cancel.set()

		def before_cancel(payment):
			# Frappe has already locked the Payment Entry before calling this hook.
			if not frappe.flags.cheque_test_attempt:
				payment_locked.set()
				self.assertTrue(allow_cancel.wait(10))
			original_before_cancel(payment)

		with (
			patch("erpnext.accounts.doctype.payment_entry.payment_entry.validate_cheque", validate),
			patch.object(PaymentEntry, "before_cancel", before_cancel),
			ThreadPoolExecutor(max_workers=2) as pool,
		):
			submission = pool.submit(
				self.run_transaction, lambda: frappe.get_doc("Payment Entry", next_payment.name).submit()
			)
			self.assertTrue(book_locked.wait(10))
			cancellation = pool.submit(
				self.run_transaction, lambda: frappe.get_doc("Payment Entry", later.name).cancel()
			)
			submission.result(timeout=20)
			cancellation.result(timeout=20)

		frappe.db.rollback()
		self.assertEqual(frappe.db.get_value("Payment Entry", next_payment.name, "docstatus"), 1)
		self.assertEqual(frappe.db.get_value("Payment Entry", later.name, "docstatus"), 2)
		self.assertEqual(get_occupied_cheque_nos(self.book), {101})
		self.book.reload()
		self.assertEqual(self.book.next_cheque_no, "000102")

	def test_concurrent_submissions_of_the_same_number_have_one_winner(self):
		payments = [self.make_payment("000101") for _ in range(2)]
		frappe.db.commit()
		barrier = Barrier(2)
		original_validate = PaymentEntry.validate

		def validate(payment):
			# Both threads hold their own Payment Entry row before trying to lock the book.
			if not frappe.flags.cheque_test_attempt:
				barrier.wait(timeout=10)
			original_validate(payment)

		def submit(name):
			try:
				frappe.get_doc("Payment Entry", name).submit()
			except frappe.ValidationError:
				frappe.db.rollback()
				return None
			return name

		with patch.object(PaymentEntry, "validate", validate), ThreadPoolExecutor(max_workers=2) as pool:
			futures = [pool.submit(self.run_transaction, lambda name=p.name: submit(name)) for p in payments]
			results = [future.result(timeout=20) for future in futures]

		frappe.db.rollback()
		winners = [name for name in results if name]
		self.assertEqual(len(winners), 1)
		self.assertEqual(get_cheque_usage(self.book.name, "000101").source_name, winners[0])
		self.assertEqual(
			sorted(frappe.db.get_value("Payment Entry", p.name, "docstatus") for p in payments), [0, 1]
		)

	def test_freed_number_is_seen_despite_an_earlier_snapshot(self):
		self.book.db_set({"cheque_end_no": "000105", "no_of_cheques": 5})
		payments = [self.make_payment(no, submit=True) for no in ("000101", "000102", "000103", "000104")]
		last = self.make_payment("000105")
		frappe.db.commit()
		snapshot_taken, cancellation_committed = Event(), Event()

		def submit_last():
			if not frappe.flags.cheque_test_attempt:
				self.assertEqual(frappe.db.get_value("Payment Entry", payments[-1].name, "docstatus"), 1)
				snapshot_taken.set()
				self.assertTrue(cancellation_committed.wait(10))
			frappe.get_doc("Payment Entry", last.name).submit()

		def cancel_earlier():
			self.assertTrue(snapshot_taken.wait(10))
			frappe.get_doc("Payment Entry", payments[-1].name).cancel()

		with ThreadPoolExecutor(max_workers=2) as pool:
			submission = pool.submit(self.run_transaction, submit_last)
			cancellation = pool.submit(self.run_transaction, cancel_earlier, committed=cancellation_committed)
			submission.result(timeout=20)
			cancellation.result(timeout=20)

		frappe.db.rollback()
		self.book.reload()
		self.assertEqual(self.book.status, "Submitted")
		self.assertEqual(get_occupied_cheque_nos(self.book), {101, 102, 103, 105})
