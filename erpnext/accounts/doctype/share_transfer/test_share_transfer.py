# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestShareTransfer(ERPNextTestSuite):
	def test_legacy_transfer_cannot_be_created(self):
		transfer = frappe.new_doc("Share Transfer")
		with self.assertRaisesRegex(frappe.ValidationError, "read-only"):
			transfer.insert(ignore_permissions=True, ignore_mandatory=True)

	def test_legacy_transfer_cannot_be_submitted(self):
		transfer = frappe.new_doc("Share Transfer")
		with self.assertRaisesRegex(frappe.ValidationError, "read-only"):
			transfer.before_submit()
