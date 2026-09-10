# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.patches.v16_0.append_fieldname_to_pos_search_fields import execute as append_fieldname
from erpnext.tests.utils import ERPNextTestSuite


class TestPOSSettings(ERPNextTestSuite):
	def setUp(self):
		self.settings = frappe.get_single("POS Settings")
		self.settings.invoice_fields = []
		self.settings.pos_search_fields = []

	def assertInvalid(self, message):
		with self.assertRaises(frappe.ValidationError) as context:
			self.settings.save()

		self.assertIn(message, str(context.exception))

	def test_invoice_field_is_validated_against_invoice_type(self):
		# consolidated_invoice exists on POS Invoice only
		self.settings.invoice_type = "POS Invoice"
		self.settings.append("invoice_fields", {"fieldname": "consolidated_invoice"})
		self.settings.save()

		self.settings.invoice_type = "Sales Invoice"
		self.assertInvalid("is not a valid field of")

	def test_field_common_to_both_invoice_types_is_allowed(self):
		for invoice_type in ("POS Invoice", "Sales Invoice"):
			self.settings.invoice_type = invoice_type
			self.settings.invoice_fields = []
			self.settings.append("invoice_fields", {"fieldname": "po_no"})
			self.settings.save()

	def test_unknown_invoice_field_is_not_allowed(self):
		self.settings.append("invoice_fields", {"fieldname": "not_a_field"})
		self.assertInvalid("is not a valid field of")

	def test_layout_invoice_field_is_not_allowed(self):
		self.settings.append("invoice_fields", {"fieldname": "accounting_dimensions_section"})
		self.assertInvalid("is not a valid field of")

	def test_invoice_field_properties_are_set_from_the_invoice(self):
		self.settings.append(
			"invoice_fields", {"fieldname": "customer", "label": "Tampered", "fieldtype": "Data"}
		)
		self.settings.save()

		field = self.settings.invoice_fields[0]
		self.assertEqual(field.label, "Customer")
		self.assertEqual(field.fieldtype, "Link")
		self.assertEqual(field.options, "Customer")

	def test_searchable_item_field_is_allowed(self):
		self.settings.append(
			"pos_search_fields", {"field": "Description (description)", "fieldname": "description"}
		)
		self.settings.save()

		self.assertEqual(self.settings.pos_search_fields[0].fieldname, "description")

	def test_excluded_search_field_is_not_allowed(self):
		self.settings.append(
			"pos_search_fields", {"field": "Item Name (item_name)", "fieldname": "item_name"}
		)
		self.assertInvalid("cannot be used to search items")

	def test_search_field_of_unsearchable_type_is_not_allowed(self):
		# maintain stock is a Check field
		self.settings.append(
			"pos_search_fields", {"field": "Maintain Stock (is_stock_item)", "fieldname": "is_stock_item"}
		)
		self.assertInvalid("cannot be used to search items")

	def test_unknown_search_field_is_not_allowed(self):
		self.settings.append(
			"pos_search_fields", {"field": "Nope (not_an_item_field)", "fieldname": "not_an_item_field"}
		)
		self.assertInvalid("cannot be used to search items")

	def test_search_field_without_a_fieldname_is_not_allowed(self):
		# the form fills the fieldname in, it cannot be picked on its own
		self.settings.append("pos_search_fields", {"field": "Description (description)"})
		self.assertInvalid("cannot be used to search items")

	def test_search_field_option_must_match_its_fieldname(self):
		self.settings.append("pos_search_fields", {"field": "Brand (brand)", "fieldname": "description"})
		self.assertInvalid("does not match")

	def test_bare_label_is_not_accepted_as_a_search_field(self):
		# the stored option carries the fieldname, the patch backfills older rows
		self.settings.append("pos_search_fields", {"field": "Description", "fieldname": "description"})
		self.assertInvalid("does not match")

	def test_duplicate_search_fields_are_not_allowed(self):
		for _ in range(2):
			self.settings.append(
				"pos_search_fields", {"field": "Description (description)", "fieldname": "description"}
			)

		self.assertInvalid("has been already added")

	def test_patch_appends_the_fieldname_to_a_legacy_search_field(self):
		self.settings.append(
			"pos_search_fields", {"field": "Description (description)", "fieldname": "description"}
		)
		self.settings.save()

		row = self.settings.pos_search_fields[0].name
		frappe.db.set_value("POS Search Fields", row, "field", "Description", update_modified=False)

		append_fieldname()

		self.assertEqual(frappe.db.get_value("POS Search Fields", row, "field"), "Description (description)")

	def test_patch_leaves_an_already_migrated_search_field_alone(self):
		self.settings.append(
			"pos_search_fields", {"field": "Description (description)", "fieldname": "description"}
		)
		self.settings.save()

		append_fieldname()

		row = self.settings.pos_search_fields[0].name
		self.assertEqual(frappe.db.get_value("POS Search Fields", row, "field"), "Description (description)")

	def test_invoice_fields_are_skipped_when_no_invoice_type_is_selected(self):
		self.settings.invoice_type = None
		self.settings.append("invoice_fields", {"fieldname": "customer"})
		self.settings.save()

		self.assertEqual(self.settings.invoice_fields[0].fieldname, "customer")
