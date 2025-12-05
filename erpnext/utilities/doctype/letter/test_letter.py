# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import nowdate

from erpnext.utilities.doctype.letter.letter import get_recipient_details

# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = ["Customer", "Supplier", "Employee", "Shareholder", "Letter Type"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]


class TestLetter(IntegrationTestCase):
	"""
	Integration tests for Letter.
	Use this class for testing interactions between multiple components.
	"""

	def setUp(self):
		frappe.db.sql("delete from `tabLetter`")

	def test_recipient_name_for_customer(self):
		"""Test that recipient_name is from customer_name field."""
		letter = create_letter(recipient_type="Customer", recipient="_Test Customer")
		letter.insert()

		customer_name = frappe.db.get_value("Customer", "_Test Customer", "customer_name")
		self.assertEqual(letter.recipient_name, customer_name)

	def test_recipient_name_for_supplier(self):
		"""Test that recipient_name is from supplier_name field."""
		letter = create_letter(recipient_type="Supplier", recipient="_Test Supplier")
		letter.insert()

		supplier_name = frappe.db.get_value("Supplier", "_Test Supplier", "supplier_name")
		self.assertEqual(letter.recipient_name, supplier_name)

	def test_recipient_name_for_employee(self):
		"""Test that recipient_name is from employee_name field."""
		employee = frappe.db.get_value("Employee", {"status": "Active"}, "name")
		if not employee:
			self.skipTest("No active employee found for testing")

		letter = create_letter(recipient_type="Employee", recipient=employee)
		letter.insert()

		employee_name = frappe.db.get_value("Employee", employee, "employee_name")
		self.assertEqual(letter.recipient_name, employee_name)

	def test_recipient_name_for_shareholder(self):
		"""Test that recipient_name is from title field for Shareholder."""
		shareholder = frappe.db.get_value("Shareholder", {}, "name")
		if not shareholder:
			self.skipTest("No shareholder found for testing")

		letter = create_letter(recipient_type="Shareholder", recipient=shareholder)
		letter.insert()

		shareholder_title = frappe.db.get_value("Shareholder", shareholder, "title")
		self.assertEqual(letter.recipient_name, shareholder_title)

	def test_recipient_name_for_contact(self):
		"""Test that recipient_name is from full_name field for Contact."""
		contact = frappe.db.get_value("Contact", {}, "name")
		if not contact:
			self.skipTest("No contact found for testing")

		letter = create_letter(recipient_type="Contact", recipient=contact)
		letter.insert()

		contact_full_name = frappe.db.get_value("Contact", contact, "full_name")
		self.assertEqual(letter.recipient_name, contact_full_name)

	def test_get_recipient_name_field_returns_correct_field(self):
		"""Test get_recipient_name_field returns the correct field name for each recipient type."""
		letter = create_letter()

		letter.recipient_type = "Customer"
		self.assertEqual(letter.get_recipient_name_field(), "customer_name")

		letter.recipient_type = "Supplier"
		self.assertEqual(letter.get_recipient_name_field(), "supplier_name")

		letter.recipient_type = "Employee"
		self.assertEqual(letter.get_recipient_name_field(), "employee_name")

		letter.recipient_type = "Shareholder"
		self.assertEqual(letter.get_recipient_name_field(), "title")

		letter.recipient_type = "Contact"
		self.assertEqual(letter.get_recipient_name_field(), "full_name")

	def test_get_recipient_returns_name_and_language(self):
		"""Test get_recipient_details whitelist function returns correct data."""
		details = get_recipient_details("Customer", "_Test Customer")

		customer_name = frappe.db.get_value("Customer", "_Test Customer", "customer_name")
		self.assertEqual(details.get("recipient_name"), customer_name)
		self.assertIn("language", details)

	def test_get_recipient_with_empty_params(self):
		"""Test get_recipient_details returns empty dict for empty params."""
		details = get_recipient_details("", "")
		self.assertEqual(details, {})

	def test_get_recipient_nonexistent_recipient(self):
		"""Test get_recipient_details raises error for non-existent recipient."""
		self.assertRaises(
			frappe.ValidationError,
			get_recipient_details,
			"Customer",
			"Non Existent Customer",
		)

	def test_recipient_name_not_set_when_recipient_empty(self):
		"""Test that recipient_name is not set when recipient is empty."""
		letter = create_letter()
		letter.recipient = None
		letter.set_recipient_name()

		self.assertIsNone(letter.recipient_name)

	def test_recipient_name_not_set_when_recipient_type_empty(self):
		"""Test that recipient_name is not set when recipient_type is empty."""
		letter = create_letter()
		letter.recipient_type = None
		letter.set_recipient_name()

		self.assertIsNone(letter.recipient_name)


def create_letter(**args):
	"""Create a Letter document for testing."""
	letter = frappe.new_doc("Letter")
	letter.recipient_type = args.get("recipient_type") or "Customer"
	letter.recipient = args.get("recipient") or "_Test Customer"
	letter.letter_type = args.get("letter_type") or "_Test Letter Type"
	letter.company = args.get("company") or "_Test Company"
	letter.date = args.get("date") or nowdate()
	letter.subject = args.get("subject") or "Test Subject"
	letter.content = args.get("content") or "Test Content"
	return letter
