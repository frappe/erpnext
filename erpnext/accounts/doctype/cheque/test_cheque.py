# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.handler import run_doc_method

from erpnext.accounts.doctype.cheque_book.test_cheque_book import make_cheque_book, make_company_bank_account
from erpnext.tests.permission_test_utils import as_user, make_fenced_user
from erpnext.tests.utils import ERPNextTestSuite


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

	def test_issued_cheque_is_cancelled_with_its_payment(self):
		frappe.db.set_value("Cheque", self.cheque.name, "status", "Issued")
		self.cheque.reload()
		with self.assertRaisesRegex(frappe.ValidationError, "Cancel the Payment Entry"):
			self.cheque.cancel_with_reason("Lost")

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


def call_from_form(cheque, http_method="POST", **args):
	"""Call cancel_with_reason the way the Cheque form does."""
	with (
		patch.object(frappe.local, "request", frappe._dict(method=http_method), create=True),
		patch.dict(frappe.response, {"docs": []}),
	):
		return run_doc_method("cancel_with_reason", dt="Cheque", dn=cheque, args=args)
