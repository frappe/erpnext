# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe

from erpnext.accounts.doctype.account.test_account import create_account
from erpnext.accounts.doctype.cheque_book.cheque_book import MAX_CHEQUES_PER_BOOK
from erpnext.tests.permission_test_utils import make_fenced_user
from erpnext.tests.utils import ERPNextTestSuite


class TestChequeBook(ERPNextTestSuite):
	def setUp(self):
		self.bank_account = make_company_bank_account()
		self.book = make_cheque_book(self.bank_account, "000101", "000105")

	def test_name_is_the_bank_account_and_the_padded_range(self):
		book = make_cheque_book(self.bank_account, " 201", "0000205", submit=False)
		self.assertEqual(book.name, f"{self.bank_account}-CHQ-000201-000205")
		self.assertEqual(
			(book.cheque_start_no, book.cheque_end_no, book.no_of_cheques), ("000201", "000205", 5)
		)

	def test_invalid_ranges_are_rejected(self):
		for start, end in (
			("110", "100"),
			("10a", "120"),
			("-100", "120"),
			("100.5", "120"),
			("1e2", "120"),
			("²", "120"),
			("1", str(MAX_CHEQUES_PER_BOOK + 1)),
		):
			with self.subTest(start=start, end=end):
				self.assertRaises(frappe.ValidationError, make_cheque_book, self.bank_account, start, end)

		for start, end in (("", "000205"), ("000201", None)):
			with self.subTest(start=start, end=end):
				self.assertRaises(frappe.MandatoryError, make_cheque_book, self.bank_account, start, end)

	def test_a_book_holds_at_most_the_limit(self):
		book = make_cheque_book(self.bank_account, "1001", str(1000 + MAX_CHEQUES_PER_BOOK))
		self.assertEqual(book.no_of_cheques, MAX_CHEQUES_PER_BOOK)
		self.assertEqual(frappe.db.count("Cheque", {"cheque_book": book.name}), MAX_CHEQUES_PER_BOOK)

	def test_submit_makes_one_available_cheque_per_leaf(self):
		self.assertEqual(self.book.status, "Submitted")
		cheques = frappe.get_all(
			"Cheque",
			filters={"cheque_book": self.book.name},
			fields=["name", "cheque_no", "status", "docstatus", "bank_account", "company"],
			order_by="name",
		)
		self.assertEqual(
			[cheque.cheque_no for cheque in cheques], ["000101", "000102", "000103", "000104", "000105"]
		)
		for cheque in cheques:
			self.assertEqual(cheque.name, f"{self.book.name}-{cheque.cheque_no}")
			self.assertEqual((cheque.status, cheque.docstatus), ("Available", 1))
			self.assertEqual((cheque.bank_account, cheque.company), (self.bank_account, self.book.company))

	def test_bank_account_and_range_are_set_only_once(self):
		other_account = make_company_bank_account("_Test Other Cheque Bank", "_Test Other Cheque Account")
		for fieldname, value in (("cheque_end_no", "000210"), ("bank_account", other_account)):
			with self.subTest(fieldname=fieldname):
				book = make_cheque_book(self.bank_account, "000201", "000205", submit=False)
				book.set(fieldname, value)
				self.assertRaises(frappe.CannotChangeConstantError, book.save)
				book.delete()

	def test_overlapping_range_is_rejected(self):
		self.assertRaises(frappe.ValidationError, make_cheque_book, self.bank_account, "000105", "000110")
		self.assertRaises(frappe.ValidationError, make_cheque_book, self.bank_account, "101", "105")
		make_cheque_book(self.bank_account, "000106", "000110")

	def test_cancelled_range_is_reused_by_amendment(self):
		self.book.cancel()
		with self.assertRaisesRegex(frappe.ValidationError, "Amend it"):
			make_cheque_book(self.bank_account, "000101", "000105")

		amended = amend(self.book)
		self.assertEqual(amended.name, f"{self.book.name}-1")
		self.assertEqual(frappe.db.count("Cheque", {"cheque_book": amended.name, "status": "Available"}), 5)

	def test_amendment_keeps_the_range(self):
		self.book.cancel()
		with self.assertRaisesRegex(frappe.ValidationError, "must keep its bank account and cheque range"):
			amend(self.book, cheque_end_no="000110")

	def test_bank_account_must_be_an_enabled_company_account(self):
		frappe.db.set_value("Bank Account", self.bank_account, "disabled", 1)
		with self.assertRaisesRegex(frappe.ValidationError, "is disabled"):
			make_cheque_book(self.bank_account, "000201", "000205")

		frappe.db.set_value("Bank Account", self.bank_account, {"disabled": 0, "is_company_account": 0})
		with self.assertRaisesRegex(frappe.ValidationError, "not a Company Account"):
			make_cheque_book(self.bank_account, "000201", "000205")

	def test_book_is_finished_when_no_cheque_is_free(self):
		frappe.db.set_value("Cheque", {"cheque_book": self.book.name}, "status", "Issued")
		lock_book(self.book).update_status()
		self.assertEqual(frappe.db.get_value("Cheque Book", self.book.name, "status"), "Finished")

		frappe.db.set_value("Cheque", f"{self.book.name}-000103", "status", "Available")
		lock_book(self.book).update_status()
		self.assertEqual(frappe.db.get_value("Cheque Book", self.book.name, "status"), "Submitted")

	def test_book_can_be_disabled_and_enabled(self):
		self.book.status = "Disabled"
		self.book.save()
		self.assertEqual(frappe.db.get_value("Cheque Book", self.book.name, "status"), "Disabled")

		# enabling a book without a free cheque makes it Finished
		frappe.db.set_value("Cheque", {"cheque_book": self.book.name}, "status", "Issued")
		self.book.status = "Submitted"
		self.book.save()
		self.assertEqual(frappe.db.get_value("Cheque Book", self.book.name, "status"), "Finished")

		for status in ("Draft", "Submitted", "Cancelled"):
			with self.subTest(status=status):
				self.book.reload()
				self.book.status = status
				self.assertRaises(frappe.ValidationError, self.book.save)

	def test_cancel_cancels_the_free_cheques(self):
		self.book.cancel()
		self.assertEqual(frappe.db.get_value("Cheque Book", self.book.name, "status"), "Cancelled")
		cheques = frappe.get_all(
			"Cheque", filters={"cheque_book": self.book.name}, fields=["status", "docstatus", "remarks"]
		)
		self.assertEqual(len(cheques), 5)
		for cheque in cheques:
			self.assertEqual((cheque.status, cheque.docstatus), ("Cancelled", 2))
			self.assertEqual(cheque.remarks, f"Cheque Book {self.book.name} cancelled")

	def test_accounts_user_can_only_read_and_select(self):
		user = make_fenced_user("cheque.user@example.com", ["Accounts User"])
		for doctype in ("Cheque Book", "Cheque"):
			for ptype, allowed in (
				("read", True),
				("select", True),
				("create", False),
				("write", False),
				("submit", False),
				("cancel", False),
			):
				with self.subTest(doctype=doctype, ptype=ptype):
					self.assertEqual(frappe.has_permission(doctype, ptype, user=user), allowed)

	def test_company_deletion_list_includes_cheque_doctypes(self):
		deletion = frappe.get_doc({"doctype": "Transaction Deletion Record", "company": self.book.company})
		deletion.insert()
		deletion.generate_to_delete_list()
		for doctype in ("Cheque Book", "Cheque"):
			with self.subTest(doctype=doctype):
				row = next(row for row in deletion.doctypes_to_delete if row.doctype_name == doctype)
				self.assertEqual(row.company_field, "company")

	def test_locks_follow_bank_account_then_book_then_cheque(self):
		book = make_cheque_book(self.bank_account, "000201", "000205", submit=False)
		locks = record_locks(book.save)
		self.assertLess(locks.index("Bank Account"), locks.index("Cheque Book"))

		cheque = frappe.get_doc("Cheque", f"{self.book.name}-000101")
		locks = record_locks(lambda: cheque.cancel_with_reason("Spoiled"))
		self.assertLess(locks.index("Cheque Book"), locks.index("Cheque"))


def make_company_bank_account(account_name="_Test Cheque Bank", bank_account_name="_Test Cheque Account"):
	account = create_account(
		account_name=account_name,
		account_type="Bank",
		company="_Test Company",
		parent_account="Bank Accounts - _TC",
	)

	if not frappe.db.exists("Bank", "_Test Cheque Bank"):
		frappe.get_doc({"doctype": "Bank", "bank_name": "_Test Cheque Bank"}).insert()

	return frappe.db.get_value("Bank Account", {"account": account}) or (
		frappe.get_doc(
			{
				"doctype": "Bank Account",
				"account_name": bank_account_name,
				"bank": "_Test Cheque Bank",
				"is_company_account": 1,
				"company": "_Test Company",
				"account": account,
			}
		)
		.insert()
		.name
	)


def make_cheque_book(bank_account, start, end, submit=True):
	book = frappe.get_doc(
		{
			"doctype": "Cheque Book",
			"bank_account": bank_account,
			"cheque_start_no": start,
			"cheque_end_no": end,
		}
	).insert()
	if submit:
		book.submit()
	return book


def amend(book, **changes):
	amended = frappe.copy_doc(book)
	amended.docstatus = 0  # copy_doc keeps the cancelled docstatus
	amended.amended_from = book.name
	amended.update(changes)
	amended.insert()
	amended.submit()
	return amended


def lock_book(book):
	return frappe.get_doc("Cheque Book", book.name, for_update=True)


def record_locks(action):
	"""Run the action and return the doctypes it locks with FOR UPDATE, in order."""
	locks = []
	get_value, get_doc = frappe.db.get_value, frappe.get_doc

	def record(fn):
		def wrapper(*args, **kwargs):
			if kwargs.get("for_update"):
				locks.append(args[0])
			return fn(*args, **kwargs)

		return wrapper

	with (
		patch.object(frappe.db, "get_value", side_effect=record(get_value)),
		patch.object(frappe, "get_doc", side_effect=record(get_doc)),
	):
		action()
	return locks
