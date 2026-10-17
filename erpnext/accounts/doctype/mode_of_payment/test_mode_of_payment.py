# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestModeofPayment(ERPNextTestSuite):
	"""Mode of Payment validates its per-company default accounts (account company
	must match the row, no company twice) and blocks disabling while a POS Profile
	still references it."""

	def setUp(self):
		frappe.set_user("Administrator")

	def test_disabling_mode_referenced_by_pos_profile_is_blocked(self):
		from erpnext.accounts.doctype.pos_profile.test_pos_profile import make_pos_profile

		make_pos_profile()  # its payments row references the "Cash" mode of payment
		cash = frappe.get_doc("Mode of Payment", "Cash")
		cash.enabled = 0
		with self.assertRaisesRegex(frappe.ValidationError, "Please remove them to disable this mode"):
			cash.save()
		self.assertEqual(frappe.db.get_value("Mode of Payment", "Cash", "enabled"), 1)


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
