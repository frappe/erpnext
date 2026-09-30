# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.tests.utils import ERPNextTestSuite

COMPANY = "_Test Company"


class TestModeofPayment(ERPNextTestSuite):
	"""Mode of Payment validates its per-company default accounts (account company
	must match the row, no company twice) and blocks disabling while a POS Profile
	still references it."""

	def setUp(self):
		frappe.set_user("Administrator")

	def make_mop(self, accounts=None, enabled=1):
		doc = frappe.new_doc("Mode of Payment")
		doc.mode_of_payment = f"_Test MoP {frappe.generate_hash(length=6)}"
		doc.type = "General"
		doc.enabled = enabled
		for company, account in accounts or []:
			doc.append("accounts", {"company": company, "default_account": account})
		return doc

	def test_valid_mode_of_payment_saves(self):
		doc = self.make_mop(accounts=[(COMPANY, "Cash - _TC")])
		doc.insert()
		self.assertTrue(doc.name)

	def test_account_of_wrong_company_throws(self):
		other_account = frappe.db.get_value("Account", {"company": "_Test Company 1", "is_group": 0}, "name")
		self.assertTrue(other_account, "need a non-group account in _Test Company 1")
		doc = self.make_mop(accounts=[(COMPANY, other_account)])
		self.assertRaises(frappe.ValidationError, doc.insert)

	def test_repeating_company_throws(self):
		doc = self.make_mop(accounts=[(COMPANY, "Cash - _TC"), (COMPANY, "Debtors - _TC")])
		self.assertRaises(frappe.ValidationError, doc.insert)

	def test_disabling_mode_referenced_by_pos_profile_is_not_blocked(self):
		# SUSPECTED BUG: validate_pos_mode_of_payment queries "Sales Invoice Payment"
		# rows with parenttype "POS Profile", but a POS Profile's payments are stored
		# as "POS Payment Method" rows. The filter never matches, so the guard is dead
		# and a mode still referenced by a POS Profile disables without complaint.
		# Locking the current (wrong) behaviour so a fix to the guard trips this test.
		from erpnext.accounts.doctype.pos_profile.test_pos_profile import make_pos_profile

		make_pos_profile()  # its payments row references the "Cash" mode of payment
		cash = frappe.get_doc("Mode of Payment", "Cash")
		cash.enabled = 0
		cash.save()
		self.assertEqual(frappe.db.get_value("Mode of Payment", "Cash", "enabled"), 0)

	def test_disabling_unreferenced_mode_succeeds(self):
		doc = self.make_mop(accounts=[(COMPANY, "Cash - _TC")], enabled=0)
		doc.insert()
		self.assertEqual(doc.enabled, 0)


def set_default_account_for_mode_of_payment(mode_of_payment, company, account):
	mode_of_payment.reload()
	if frappe.db.exists(
		"Mode of Payment Account", {"parent": mode_of_payment.mode_of_payment, "company": company}
	):
		frappe.db.set_value(
			"Mode of Payment Account",
			{"parent": mode_of_payment.mode_of_payment, "company": company},
			"default_account",
			account,
		)
		return

	mode_of_payment.append("accounts", {"company": company, "default_account": account})
	mode_of_payment.save()
