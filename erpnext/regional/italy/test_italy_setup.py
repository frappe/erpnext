# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from erpnext.regional.italy.setup import setup_customer_name_fields


class TestItalySetup(IntegrationTestCase):
	def tearDown(self):
		# Clean up Property Setters created during tests
		for ps in frappe.get_all(
			"Property Setter",
			filters={"doc_type": "Customer", "field_name": ["in", ["first_name", "last_name"]]},
		):
			frappe.delete_doc("Property Setter", ps.name, force=True)

		# Clean up Client Script
		if frappe.db.exists("Client Script", "Italy - Customer Name Fields"):
			frappe.delete_doc("Client Script", "Italy - Customer Name Fields", force=True)

		# Clean up any leftover Custom Fields
		for fieldname in ("first_name", "last_name", "test_italy_setup_field"):
			cf_name = f"Customer-{fieldname}"
			if frappe.db.exists("Custom Field", cf_name):
				frappe.delete_doc("Custom Field", cf_name, force=True)

	def test_property_setters_created(self):
		"""Property Setters should make first_name/last_name editable and visible."""
		setup_customer_name_fields()

		for fieldname in ("first_name", "last_name"):
			fieldtype_ps = frappe.db.get_value(
				"Property Setter",
				{"doc_type": "Customer", "field_name": fieldname, "property": "fieldtype"},
				"value",
			)
			self.assertEqual(fieldtype_ps, "Data")

			hidden_ps = frappe.db.get_value(
				"Property Setter",
				{"doc_type": "Customer", "field_name": fieldname, "property": "hidden"},
				"value",
			)
			self.assertEqual(hidden_ps, "0")

			fetch_from_ps = frappe.db.get_value(
				"Property Setter",
				{"doc_type": "Customer", "field_name": fieldname, "property": "fetch_from"},
				"value",
			)
			self.assertEqual(fetch_from_ps, "")

			depends_on_ps = frappe.db.get_value(
				"Property Setter",
				{"doc_type": "Customer", "field_name": fieldname, "property": "depends_on"},
				"value",
			)
			self.assertEqual(depends_on_ps, 'eval:doc.customer_type!="Company"')

			print_hide_ps = frappe.db.get_value(
				"Property Setter",
				{"doc_type": "Customer", "field_name": fieldname, "property": "print_hide"},
				"value",
			)
			self.assertEqual(print_hide_ps, "1")

	def test_client_script_created(self):
		"""Client Script should be created to reposition fields."""
		setup_customer_name_fields()
		self.assertTrue(frappe.db.exists("Client Script", "Italy - Customer Name Fields"))

	def test_duplicate_custom_fields_cleaned_up(self):
		"""Old duplicate Custom Fields should be removed."""
		# Simulate the old regional setup creating duplicate Custom Fields
		for fieldname in ("first_name", "last_name"):
			cf_name = f"Customer-{fieldname}"
			if not frappe.db.exists("Custom Field", cf_name):
				cf = frappe.get_doc(
					{
						"doctype": "Custom Field",
						"dt": "Customer",
						"fieldname": fieldname,
						"fieldtype": "Data",
						"label": fieldname.replace("_", " ").title(),
					}
				)
				cf.flags.ignore_validate = True
				cf.insert()

		# Run the setup — it should clean up the duplicates
		setup_customer_name_fields()

		for fieldname in ("first_name", "last_name"):
			self.assertFalse(frappe.db.exists("Custom Field", f"Customer-{fieldname}"))

	def test_no_unique_fieldname_error_after_setup(self):
		"""Adding custom fields to Customer should work after setup."""
		setup_customer_name_fields()

		cf = frappe.get_doc(
			{
				"doctype": "Custom Field",
				"dt": "Customer",
				"fieldname": "test_italy_setup_field",
				"fieldtype": "Data",
				"label": "Test Italy Setup Field",
				"insert_after": "customer_name",
			}
		)
		cf.insert()
		self.assertTrue(frappe.db.exists("Custom Field", "Customer-test_italy_setup_field"))
		cf.delete()

	def test_idempotent(self):
		"""Running setup twice should not raise errors or create duplicates."""
		setup_customer_name_fields()
		setup_customer_name_fields()

		for fieldname in ("first_name", "last_name"):
			ps_count = frappe.db.count(
				"Property Setter",
				filters={"doc_type": "Customer", "field_name": fieldname},
			)
			self.assertEqual(ps_count, 5)
