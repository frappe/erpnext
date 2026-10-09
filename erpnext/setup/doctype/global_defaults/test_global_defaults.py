# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestGlobalDefaults(ERPNextTestSuite):
	def test_unrelated_save_preserves_pos_profile_rounding(self):
		defaults = frappe.get_doc("Global Defaults")
		defaults._doc_before_save = frappe._dict(disable_rounded_total=defaults.disable_rounded_total)

		with (
			patch("frappe.db.set_default"),
			patch("frappe.db.set_value"),
			patch("frappe.clear_cache"),
			patch.object(defaults, "toggle_rounded_total"),
			patch.object(defaults, "toggle_in_words"),
			patch.object(defaults, "set_disable_rounded_total_on_pos_profiles") as update_profiles,
		):
			defaults.on_update()
			update_profiles.assert_not_called()

			defaults.disable_rounded_total = 1 - int(defaults.disable_rounded_total)
			defaults.on_update()
			update_profiles.assert_called_once_with()

	def test_disable_in_words_covers_visible_payment_and_subcontracting_fields(self):
		for disabled in (1, 0):
			with self.subTest(disabled=disabled):
				with self.change_settings("Global Defaults", disable_in_words=disabled):
					for doctype in ("Payment Entry", "Subcontracting Receipt"):
						field = frappe.get_meta(doctype).get_field("in_words")
						self.assertEqual(field.hidden, disabled)
						self.assertEqual(field.print_hide, disabled)
