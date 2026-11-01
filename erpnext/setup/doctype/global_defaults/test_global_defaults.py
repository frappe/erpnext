# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase, change_settings


class TestGlobalDefaults(FrappeTestCase):
	def test_disable_in_words_covers_payment_and_subcontracting_receipt(self):
		for disabled in (1, 0):
			with self.subTest(disabled=disabled):
				with change_settings("Global Defaults", disable_in_words=disabled):
					for doctype in ("Payment Entry", "Subcontracting Receipt"):
						field = frappe.get_meta(doctype).get_field("in_words")
						self.assertEqual(field.hidden, disabled)
						self.assertEqual(field.print_hide, disabled)
