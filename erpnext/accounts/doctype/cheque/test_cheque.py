# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.handler import run_doc_method
from frappe.utils import getdate

from erpnext.accounts.doctype.cheque.cheque import Cheque
from erpnext.accounts.doctype.cheque.cheque_payment import (
	cancel_cheque_payment,
	get_cheque_summary,
	get_next_cheque,
	lock_cheque,
	validate_cheque,
)
from erpnext.accounts.doctype.cheque_book.test_cheque_book import (
	make_cheque_book,
	make_company_bank_account,
	record_locks,
)
from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry
from erpnext.tests.permission_test_utils import as_user, make_fenced_user
from erpnext.tests.utils import ERPNextTestSuite

BANK_LEDGER = "_Test Cheque Bank - _TC"


class TestCheque(ERPNextTestSuite):
	def setUp(self):
		self.book = make_cheque_book(make_company_bank_account(), "000101", "000105")
		self.cheque = frappe.get_doc("Cheque", f"{self.book.name}-000101")

	def test_cheque_cannot_be_created_or_changed_by_hand(self):
		new_cheque = frappe.copy_doc(self.cheque)
		new_cheque.update({"docstatus": 0, "cheque_no": "000999"})
		self.assertRaisesRegex(frappe.ValidationError, "changes only through", new_cheque.insert)

		self.cheque.remarks = "Edited by hand"
		self.assertRaisesRegex(frappe.ValidationError, "changes only through", self.cheque.save)

		cheque = frappe.get_doc("Cheque", self.cheque.name)
		self.assertRaisesRegex(frappe.ValidationError, "changes only through", cheque.cancel)

	def test_cancel_with_reason(self):
		# Frappe saves no versions in tests unless in_test is off
		with patch.object(frappe, "in_test", False):
			self.cheque.cancel_with_reason(" Spoiled ", "Torn while writing")

		self.cheque.reload()
		self.assertEqual((self.cheque.docstatus, self.cheque.status), (2, "Cancelled"))
		self.assertEqual(self.cheque.cancellation_reason, "Spoiled")
		self.assertEqual(self.cheque.remarks, "Torn while writing")
		self.assertEqual(frappe.db.get_value("Cheque Book", self.book.name, "status"), "Submitted")

		version = frappe.db.get_value(
			"Version", {"ref_doctype": "Cheque", "docname": self.cheque.name}, "data"
		)
		self.assertIn(["status", "Available", "Cancelled"], frappe.parse_json(version)["changed"])

	def test_reason_is_required(self):
		self.assertRaises(frappe.MandatoryError, self.cheque.cancel_with_reason, "  ")

	def test_cancelling_the_last_free_cheque_finishes_the_book(self):
		for name in frappe.get_all("Cheque", filters={"cheque_book": self.book.name}, pluck="name"):
			frappe.get_doc("Cheque", name).cancel_with_reason("Lost")
		self.assertEqual(frappe.db.get_value("Cheque Book", self.book.name, "status"), "Finished")

	def test_only_accounts_manager_can_cancel_a_cheque(self):
		user = make_fenced_user("cheque.user@example.com", ["Accounts User"])
		with as_user(user):
			self.assertRaises(frappe.PermissionError, call_from_form, self.cheque.name, reason="Spoiled")

		manager = make_fenced_user("cheque.manager@example.com", ["Accounts Manager"])
		with as_user(manager):
			self.assertRaises(
				frappe.PermissionError, call_from_form, self.cheque.name, http_method="GET", reason="Spoiled"
			)
			call_from_form(self.cheque.name, reason="Spoiled")
		self.assertEqual(frappe.db.get_value("Cheque", self.cheque.name, "docstatus"), 2)


class TestChequePayment(ERPNextTestSuite):
	def setUp(self):
		if not frappe.db.exists("Mode of Payment", "Cheque"):
			frappe.get_doc(
				{"doctype": "Mode of Payment", "mode_of_payment": "Cheque", "type": "Bank"}
			).insert()
		self.bank_account = make_company_bank_account()
		self.book = make_cheque_book(self.bank_account, "000101", "000105")

	def name_of(self, cheque_no, book=None):
		return f"{(book or self.book).name}-{cheque_no}"

	def pay(self, cheque_no=None, submit=True, book=None, **args):
		"""Make a cheque payment from the test bank ledger. With no cheque number, take the suggestion."""
		args.setdefault("paid_from", BANK_LEDGER)
		payment = create_payment_entry(**args)
		payment.mode_of_payment = "Cheque"
		payment.cheque = self.name_of(cheque_no, book) if cheque_no else get_next_cheque(payment.paid_from)
		payment.save()
		if submit:
			payment.submit()
		return payment

	def test_suggestion_follows_the_highest_used_cheque(self):
		self.assertEqual(get_next_cheque(BANK_LEDGER), self.name_of("000101"))

		self.pay("000103")
		self.assertEqual(get_next_cheque(BANK_LEDGER), self.name_of("000104"))

		frappe.get_doc("Cheque", self.name_of("000104")).cancel_with_reason("Spoiled")
		self.assertEqual(get_next_cheque(BANK_LEDGER), self.name_of("000105"))

	def test_suggestion_moves_to_the_next_book(self):
		self.pay("000105")
		self.assertIsNone(get_next_cheque(BANK_LEDGER))  # 000101 to 000104 stay free for a manual pick

		book = make_cheque_book(self.bank_account, "000201", "000205")
		self.assertEqual(get_next_cheque(BANK_LEDGER), self.name_of("000201", book))

	def test_disabled_book_or_bank_account_gets_no_suggestion(self):
		self.book.status = "Disabled"
		self.book.save()
		self.assertIsNone(get_next_cheque(BANK_LEDGER))

		self.book.status = "Submitted"
		self.book.save()
		frappe.db.set_value("Bank Account", self.bank_account, "disabled", 1)
		self.assertIsNone(get_next_cheque(BANK_LEDGER))

	def test_summary_shows_the_range_and_the_free_count(self):
		self.pay("000101")
		self.assertEqual(
			get_cheque_summary(self.name_of("000102")),
			{"cheque_no": "000102", "cheque_start_no": "000101", "cheque_end_no": "000105", "free": 4},
		)

	def test_submit_records_the_payment_on_the_cheque(self):
		payment = self.pay(paid_amount=2500)
		self.assertEqual(payment.reference_no, "000101")

		cheque = frappe.get_doc("Cheque", self.name_of("000101"))
		self.assertEqual((cheque.status, cheque.payment_entry), ("Issued", payment.name))
		self.assertEqual((cheque.party_name, cheque.amount), (payment.party_name, 2500))
		self.assertEqual(getdate(cheque.cheque_date), getdate(payment.reference_date))

	def test_payment_on_the_last_cheque_finishes_the_book(self):
		book = make_cheque_book(self.bank_account, "000201", "000201")
		self.pay("000201", book=book)
		self.assertEqual(frappe.db.get_value("Cheque Book", book.name, "status"), "Finished")

	def test_cheque_must_match_the_payment(self):
		with self.assertRaisesRegex(frappe.ValidationError, "Account Paid From"):
			self.pay("000101", paid_from="_Test Bank - _TC")

		self.book.status = "Disabled"
		self.book.save()
		self.assertRaisesRegex(frappe.ValidationError, "is disabled", self.pay, "000101")

		self.book.status = "Submitted"
		self.book.save()
		frappe.db.set_value("Bank Account", self.bank_account, "disabled", 1)
		self.assertRaisesRegex(frappe.ValidationError, "enabled Company Account", self.pay, "000101")

	def test_used_or_cancelled_cheque_is_rejected(self):
		self.pay("000101")
		self.assertRaisesRegex(frappe.ValidationError, "already used", self.pay, "000101")

		frappe.get_doc("Cheque", self.name_of("000102")).cancel_with_reason("Lost")
		self.assertRaises(frappe.CancelledLinkError, self.pay, "000102")

	def test_first_submit_wins_when_two_drafts_take_a_cheque(self):
		first = self.pay("000101", submit=False)
		second = self.pay("000101", submit=False)
		first.submit()
		self.assertRaisesRegex(frappe.ValidationError, "already used", second.submit)

	def test_other_payment_modes_drop_the_cheque(self):
		payment = self.pay("000101", submit=False)
		payment.mode_of_payment = "Cash"
		payment.save()
		self.assertIsNone(payment.cheque)

	def test_issued_cheque_is_cancelled_with_its_payment(self):
		payment = self.pay("000101")
		cheque = frappe.get_doc("Cheque", self.name_of("000101"))
		with self.assertRaisesRegex(frappe.ValidationError, "Cancel the Payment Entry"):
			cheque.cancel_with_reason("Lost")
		frappe.db.savepoint("book_cancel")  # the refused cancel has already written docstatus 2
		with self.assertRaisesRegex(frappe.ValidationError, "000101"):
			self.book.cancel()
		frappe.db.rollback(save_point="book_cancel")

		payment.cancel()
		cheque.reload()
		self.assertEqual(
			(cheque.docstatus, cheque.status, cheque.payment_entry), (2, "Cancelled", payment.name)
		)
		self.assertIsNone(cheque.cancellation_reason)
		self.assertEqual(cheque.remarks, f"Cancelled with Payment Entry {payment.name}")
		self.assertEqual(get_next_cheque(BANK_LEDGER), self.name_of("000102"))

	def test_cancel_endpoint_records_the_reason(self):
		payment = self.pay("000101")
		cancel_cheque_payment(payment.name, " Spoiled ", "Printer jam")

		self.assertEqual(frappe.db.get_value("Payment Entry", payment.name, "docstatus"), 2)
		cheque = frappe.get_doc("Cheque", self.name_of("000101"))
		self.assertEqual(cheque.status, "Cancelled")
		self.assertEqual((cheque.cancellation_reason, cheque.remarks), ("Spoiled", "Printer jam"))

	def test_cancel_endpoint_needs_a_reason(self):
		payment = self.pay("000101")
		self.assertRaises(frappe.MandatoryError, cancel_cheque_payment, payment.name, " ")
		self.assertEqual(frappe.db.get_value("Payment Entry", payment.name, "docstatus"), 1)

	def test_failed_cancel_keeps_the_payment_and_the_cheque(self):
		payment = self.pay("000101")
		frappe.db.savepoint("cheque_cancel")
		with patch.object(Cheque, "void", side_effect=frappe.ValidationError("Void failed")):
			self.assertRaisesRegex(
				frappe.ValidationError, "Void failed", cancel_cheque_payment, payment.name, "Spoiled"
			)
		frappe.db.rollback(save_point="cheque_cancel")

		self.assertEqual(frappe.db.get_value("Payment Entry", payment.name, "docstatus"), 1)
		cheque = frappe.get_doc("Cheque", self.name_of("000101"))
		self.assertEqual((cheque.status, cheque.cancellation_reason), ("Issued", None))

	def test_amended_payment_needs_a_new_cheque(self):
		payment = self.pay("000101")
		payment.cancel()

		amended = frappe.copy_doc(payment)
		amended.docstatus = 0  # copy_doc keeps the cancelled docstatus in tests
		amended.amended_from = payment.name
		self.assertRaises(frappe.CancelledLinkError, amended.insert)

		amended.cheque = get_next_cheque(BANK_LEDGER)
		amended.insert()
		amended.submit()
		self.assertEqual(amended.reference_no, "000102")

	def test_accounts_user_uses_cheques_through_payments(self):
		user = make_fenced_user("cheque.user@example.com", ["Accounts User"])
		payment = self.pay("000101", submit=False)
		with as_user(user):
			frappe.get_doc("Payment Entry", payment.name).submit()
			cancel_cheque_payment(payment.name, "Spoiled")

		cheque = frappe.get_doc("Cheque", self.name_of("000101"))
		self.assertEqual((cheque.status, cheque.cancellation_reason), ("Cancelled", "Spoiled"))

	def test_suggestion_and_validation_keep_their_query_budgets(self):
		make_cheque_book(self.bank_account, "000201", "000205")
		self.pay("000102")
		payment = self.pay(submit=False)
		get_next_cheque(BANK_LEDGER)  # load the meta and permission caches first
		validate_cheque(payment)

		queries = count_queries(lambda: get_next_cheque(BANK_LEDGER))
		self.assertTrue(0 < len(queries) <= 3, queries)  # bank accounts, books, used cheques
		queries = count_queries(lambda: validate_cheque(payment))
		self.assertTrue(0 < len(queries) <= 2, queries)  # the cheque with its book and bank account, drafts

	def test_submit_locks_the_book_before_the_cheque(self):
		payment = self.pay("000101", submit=False)
		locks = record_locks(payment.submit)
		self.assertLess(locks.index("Cheque Book"), locks.index("Cheque"))

	def test_missing_cheque_is_refused_before_any_lock(self):
		locks = record_locks(lambda: self.assertRaises(frappe.DoesNotExistError, lock_cheque, "missing"))
		self.assertEqual(locks, [])


def count_queries(action):
	"""Run the action and return the SQL queries that it sends."""
	queries = []
	sql = frappe.db.sql

	def record(query, *args, **kwargs):
		queries.append(str(query))
		return sql(query, *args, **kwargs)

	with patch.object(frappe.db, "sql", side_effect=record):
		action()
	return queries


def call_from_form(cheque, http_method="POST", **args):
	"""Call cancel_with_reason the way the Cheque form does."""
	with (
		patch.object(frappe.local, "request", frappe._dict(method=http_method), create=True),
		patch.dict(frappe.response, {"docs": []}),
	):
		return run_doc_method("cancel_with_reason", dt="Cheque", dn=cheque, args=args)
