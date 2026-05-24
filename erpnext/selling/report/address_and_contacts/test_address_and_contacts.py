# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe

from erpnext.selling.report.address_and_contacts.address_and_contacts import execute, get_columns
from erpnext.tests.utils import ERPNextTestSuite


class TestAddressAndContacts(ERPNextTestSuite):
	def setUp(self):
		self.customer = create_test_customer()
		self.contact = create_test_contact(self.customer.name)

	def test_address_and_contacts_returns_data(self):
		"""Test that the report returns data for a valid party type."""
		filters = frappe._dict(party_type="Customer")
		_, data = execute(filters)
		self.assertTrue(len(data) > 0, "Report should return at least one row")

	def test_address_and_contacts_columns_include_designation(self):
		"""Test that the designation column is present in the report columns."""
		filters = frappe._dict(party_type="Customer")
		columns = get_columns(filters)
		col_labels = [col.get("label", "").lower() if isinstance(col, dict) else str(col).lower() for col in columns]
		self.assertTrue(any("designation" in label for label in col_labels), "Designation column should be present")

	def test_address_and_contacts_filter_by_party(self):
		"""Test that filtering by specific party returns only that party data."""
		filters = frappe._dict(party_type="Customer", party_name=self.customer.name)
		_, data = execute(filters)
		self.assertTrue(len(data) > 0, "Should return at least one row for party filter")
		for row in data:
			self.assertEqual(row[0], self.customer.name, "Should only return rows for the filtered customer")

	def test_address_and_contacts_empty_party_type(self):
		"""Test that an empty party_type returns no data gracefully."""
		filters = frappe._dict(party_type=None)
		_, data = execute(filters)
		self.assertEqual(data, [], "Empty party_type should return empty data")


def create_test_customer():
	customer = frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": "_Test Customer Designation Report",
			"customer_type": "Individual",
			"customer_group": "Individual",
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
			"links": [{"link_doctype": "Customer", "link_name": customer_name}],
		}
	)
	contact.insert(ignore_permissions=True)
	return contact

