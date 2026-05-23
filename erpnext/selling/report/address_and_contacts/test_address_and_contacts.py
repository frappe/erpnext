# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe

from erpnext.selling.report.address_and_contacts.address_and_contacts import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestAddressAndContacts(ERPNextTestSuite):
	def setUp(self):
		self.customer = create_test_customer()
		self.contact = create_test_contact(self.customer.name)

	def tearDown(self):
		try:
			frappe.delete_doc("Contact", self.contact.name, force=True)
			frappe.delete_doc("Customer", self.customer.name, force=True)
		finally:
			super().tearDown()

	def test_address_and_contacts_returns_data(self):
		"""Test that the report returns data for a valid party type."""
		filters = frappe._dict(party_type="Customer")

		_, data = execute(filters)

		self.assertTrue(len(data) > 0, "Report should return at least one row")

	def test_address_and_contacts_columns_include_designation(self):
		"""Test that the designation column is present in the report output."""
		filters = frappe._dict(party_type="Customer")

		columns, _ = execute(filters)

		col_labels = []
		for col in columns:
			if isinstance(col, dict):
				col_labels.append(col.get("label", "").lower())
			else:
				col_labels.append(str(col).lower())

		self.assertTrue(
			any("designation" in label for label in col_labels),
			"Designation column should be present in Address and Contacts report",
		)

	def test_address_and_contacts_filter_by_party(self):
		"""Test that filtering by specific party returns only that party's data."""
		filters = frappe._dict(
			party_type="Customer",
			party_name=self.customer.name,
		)

		_, data = execute(filters)

		self.assertTrue(len(data) > 0, "Should return at least one row for party filter")
		for row in data:
			self.assertEqual(
				row[0],
				self.customer.name,
				"Report should only return rows for the filtered customer",
			)

	def test_address_and_contacts_empty_party_type(self):
		"""Test that an empty party_type returns no data gracefully."""
		filters = frappe._dict(party_type=None)

		_, data = execute(filters)

		self.assertEqual(data, [], "Empty party_type should return empty data")

	def test_contact_designation_in_report_data(self):
		"""Test that designation from contact appears in report rows."""
		filters = frappe._dict(
			party_type="Customer",
			party_name=self.customer.name,
		)

		_, data = execute(filters)

		self.assertTrue(len(data) > 0, "Should return at least one row")
		designations = []
		for row in data:
			if isinstance(row, (list, tuple)):
				designations.extend([str(cell) for cell in row])

		self.assertTrue(
			any("_Test Designation" in d for d in designations),
			"Contact designation should appear in report data",
		)


def create_test_customer():
	customer = frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": "_Test Customer Designation Report",
			"customer_type": "Individual",
			"customer_group": "All Customer Groups",
			"territory": "All Territories",
		}
	)
	customer.insert(ignore_permissions=True)
	return customer


def create_test_contact(customer_name):
	contact = frappe.get_doc(
		{
			"doctype": "Contact",
			"first_name": "_Test",
			"last_name": "Contact Designation",
			"designation": "_Test Designation",
			"links": [
				{
					"link_doctype": "Customer",
					"link_name": customer_name,
				}
			],
		}
	)
	contact.insert(ignore_permissions=True)
	return contact