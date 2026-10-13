# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestShareType(ERPNextTestSuite):
	def test_legacy_share_type_cannot_be_created(self):
		share_type = frappe.new_doc("Share Type")
		share_type.title = "Old Equity"
		with self.assertRaisesRegex(frappe.ValidationError, "read-only"):
			share_type.insert(ignore_permissions=True)
