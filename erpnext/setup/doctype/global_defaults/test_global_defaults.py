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
		defaults = frappe.get_doc("Global Defaults")
		defaults.disable_in_words = 1

		with patch(
			"erpnext.setup.doctype.global_defaults.global_defaults.make_property_setter"
		) as make_setter:
			defaults.toggle_in_words()

		for doctype in ("Payment Entry", "Subcontracting Receipt"):
			for property_name in ("hidden", "print_hide"):
				self.assertIn(
					(doctype, "in_words", property_name, 1, "Check"),
					[call.args for call in make_setter.call_args_list],
				)

		# Journal Entry's words field is already hidden and print-hidden by default.
		self.assertNotIn("Journal Entry", [call.args[0] for call in make_setter.call_args_list])
