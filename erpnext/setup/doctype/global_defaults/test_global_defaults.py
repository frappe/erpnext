# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.www.printview import is_visible

from erpnext.tests.utils import ERPNextTestSuite


class TestGlobalDefaults(ERPNextTestSuite):
	def test_disable_in_words_preserves_payment_and_subcontracting_print_defaults(self):
		for doctype in ("Payment Entry", "Subcontracting Receipt"):
			make_property_setter(doctype, "in_words", "print_hide", 1, "Check")

		with self.change_settings("Global Defaults", disable_in_words=0):
			defaults = frappe.get_doc("Global Defaults")
			for disabled in (0, 1, 0):
				with self.subTest(disabled=disabled):
					defaults.disable_in_words = disabled
					defaults.save()
					for doctype in ("Payment Entry", "Subcontracting Receipt"):
						field = frappe.get_meta(doctype).get_field("in_words")
						self.assertEqual(field.hidden, disabled)
						self.assertEqual(field.print_hide, 1)
						doc = frappe.new_doc(doctype)
						doc.in_words = "INR One Hundred only."
						self.assertFalse(is_visible(field, doc))

					field = frappe.get_meta("Sales Invoice").get_field("in_words")
					self.assertEqual(field.hidden, disabled)
					self.assertEqual(field.print_hide, disabled)

			defaults.hide_currency_symbol = "No" if defaults.hide_currency_symbol == "Yes" else "Yes"
			defaults.save()
			for doctype in ("Payment Entry", "Subcontracting Receipt"):
				self.assertEqual(frappe.get_meta(doctype).get_field("in_words").print_hide, 1)

	def test_disable_in_words_preserves_custom_print_visibility(self):
		for doctype in ("Payment Entry", "Subcontracting Receipt"):
			make_property_setter(doctype, "in_words", "print_hide", 0, "Check", is_system_generated=False)

		for disabled in (1, 0):
			with self.change_settings("Global Defaults", disable_in_words=disabled):
				for doctype in ("Payment Entry", "Subcontracting Receipt"):
					field = frappe.get_meta(doctype).get_field("in_words")
					self.assertEqual(field.hidden, disabled)
					self.assertEqual(field.print_hide, 0)

	def test_restore_in_words_print_defaults_patch(self):
		from erpnext.patches.v16_0.restore_in_words_print_defaults import execute

		for value in (0, 1):
			with self.subTest(value=value):
				for doctype in ("Payment Entry", "Subcontracting Receipt"):
					make_property_setter(doctype, "in_words", "print_hide", value, "Check")
					make_property_setter(doctype, "in_words", "hidden", 1, "Check")

				execute()
				execute()

				for doctype in ("Payment Entry", "Subcontracting Receipt"):
					self.assertFalse(
						frappe.db.exists(
							"Property Setter",
							{"doc_type": doctype, "field_name": "in_words", "property": "print_hide"},
						)
					)
					field = frappe.get_meta(doctype).get_field("in_words")
					self.assertEqual(field.print_hide, 1)
					self.assertEqual(field.hidden, 1)

	def test_restore_in_words_print_defaults_preserves_other_property_setters(self):
		from erpnext.patches.v16_0.restore_in_words_print_defaults import execute

		for doctype in ("Payment Entry", "Subcontracting Receipt"):
			make_property_setter(doctype, "in_words", "print_hide", 0, "Check", is_system_generated=False)
		make_property_setter("Sales Invoice", "in_words", "print_hide", 0, "Check")

		execute()

		for doctype in ("Payment Entry", "Subcontracting Receipt", "Sales Invoice"):
			self.assertEqual(frappe.get_meta(doctype).get_field("in_words").print_hide, 0)
