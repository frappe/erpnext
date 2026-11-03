# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestGlobalDefaults(ERPNextTestSuite):
	def test_disable_in_words_covers_payment_and_subcontracting_receipt(self):
		for disabled in (1, 0):
			with self.subTest(disabled=disabled):
				with self.change_settings("Global Defaults", disable_in_words=disabled):
					for doctype in ("Payment Entry", "Subcontracting Receipt"):
						field = frappe.get_meta(doctype).get_field("in_words")
						self.assertEqual(field.hidden, disabled)
						self.assertEqual(field.print_hide, disabled)
