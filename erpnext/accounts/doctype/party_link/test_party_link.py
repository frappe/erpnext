# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe import _

from erpnext.accounts.doctype.party_link.party_link import (
	_copy_address_and_contacts,
	_find_party_link,
	create_and_link_party,
	create_party_link,
	remove_party_link,
)
from erpnext.accounts.party import load_party_link
from erpnext.tests.utils import ERPNextTestSuite


class TestPartyLink(ERPNextTestSuite):
	def setUp(self):
		self.customer = _make_customer("_Test Party Link Customer")
		self.supplier = _make_supplier("_Test Party Link Supplier")

	def test_create_party_link(self):
		link = create_party_link("Supplier", self.supplier.name, self.customer.name)
		self.assertEqual(link.primary_role, "Supplier")
		self.assertEqual(link.primary_party, self.supplier.name)
		self.assertEqual(link.secondary_role, "Customer")
		self.assertEqual(link.secondary_party, self.customer.name)
		self.assertTrue(frappe.db.exists("Party Link", link.name))

	def test_find_party_link_from_primary_side(self):
		link = create_party_link("Supplier", self.supplier.name, self.customer.name)
		found = _find_party_link("Supplier", self.supplier.name)
		self.assertIsNotNone(found)
		self.assertEqual(found.name, link.name)

	def test_find_party_link_from_secondary_side(self):
		link = create_party_link("Supplier", self.supplier.name, self.customer.name)
		found = _find_party_link("Customer", self.customer.name)
		self.assertIsNotNone(found)
		self.assertEqual(found.name, link.name)

	def test_find_party_link_returns_none_when_no_link(self):
		result = _find_party_link("Supplier", self.supplier.name)
		self.assertIsNone(result)

	def test_load_party_link_on_supplier_sets_onload(self):
		create_party_link("Supplier", self.supplier.name, self.customer.name)
		supplier_doc = frappe.get_doc("Supplier", self.supplier.name)
		load_party_link(supplier_doc)
		onload = supplier_doc.get_onload("party_link")
		self.assertEqual(onload["name"], self.customer.name)
		self.assertEqual(onload["role"], "Customer")

	def test_load_party_link_on_customer_sets_onload(self):
		create_party_link("Supplier", self.supplier.name, self.customer.name)
		customer_doc = frappe.get_doc("Customer", self.customer.name)
		load_party_link(customer_doc)
		onload = customer_doc.get_onload("party_link")
		self.assertEqual(onload["name"], self.supplier.name)
		self.assertEqual(onload["role"], "Supplier")

	def test_load_party_link_does_nothing_when_no_link(self):
		supplier_doc = frappe.get_doc("Supplier", self.supplier.name)
		load_party_link(supplier_doc)
		self.assertIsNone(supplier_doc.get_onload().get("party_link"))

	def test_remove_party_link(self):
		link = create_party_link("Supplier", self.supplier.name, self.customer.name)
		remove_party_link("Supplier", self.supplier.name)
		self.assertFalse(frappe.db.exists("Party Link", link.name))

	def test_remove_party_link_throws_when_not_found(self):
		self.assertRaises(
			frappe.exceptions.ValidationError, remove_party_link, "Supplier", self.supplier.name
		)

	def test_create_and_link_party_creates_customer_and_link(self):
		result = create_and_link_party(
			primary_role="Supplier",
			primary_party=self.supplier.name,
			new_party_name="_Test Auto Customer",
			new_party_type="Company",
		)
		self.assertEqual(result.primary_role, "Supplier")
		self.assertEqual(result.primary_party, self.supplier.name)
		self.assertEqual(result.secondary_role, "Customer")
		linked_customer = frappe.db.get_value("Customer", result.secondary_party, "customer_name")
		self.assertEqual(linked_customer, "_Test Auto Customer")

	def test_create_and_link_party_creates_supplier_and_link(self):
		result = create_and_link_party(
			primary_role="Customer",
			primary_party=self.customer.name,
			new_party_name="_Test Auto Supplier",
			new_party_type="Company",
		)
		self.assertEqual(result.primary_role, "Customer")
		self.assertEqual(result.primary_party, self.customer.name)
		self.assertEqual(result.secondary_role, "Supplier")
		linked_supplier = frappe.db.get_value("Supplier", result.secondary_party, "supplier_name")
		self.assertEqual(linked_supplier, "_Test Auto Supplier")

	def test_copy_address_and_contacts_links_address_to_secondary(self):
		address = _make_address("_Test PL Address", "Supplier", self.supplier.name)
		link = create_party_link("Supplier", self.supplier.name, self.customer.name)
		_copy_address_and_contacts(link)

		linked = frappe.db.exists(
			"Dynamic Link",
			{
				"parenttype": "Address",
				"parent": address.name,
				"link_doctype": "Customer",
				"link_name": self.customer.name,
			},
		)
		self.assertTrue(linked)

	def test_copy_address_and_contacts_skips_already_linked(self):
		address = _make_address("_Test PL Address Dup", "Supplier", self.supplier.name)
		link = create_party_link("Supplier", self.supplier.name, self.customer.name)

		_copy_address_and_contacts(link)
		_copy_address_and_contacts(link)

		count = frappe.db.count(
			"Dynamic Link",
			{
				"parenttype": "Address",
				"parent": address.name,
				"link_doctype": "Customer",
				"link_name": self.customer.name,
			},
		)
		self.assertEqual(count, 1)


def _make_customer(customer_name):
	if frappe.db.exists("Customer", {"customer_name": customer_name}):
		return frappe.get_doc("Customer", {"customer_name": customer_name})
	doc = frappe.new_doc("Customer")
	doc.customer_name = customer_name
	doc.customer_type = "Company"
	doc.customer_group = frappe.db.get_value("Customer Group", {"is_group": 0}, "name")
	doc.territory = frappe.db.get_single_value("Selling Settings", "territory") or "All Territories"
	doc.insert(ignore_permissions=True)
	return doc


def _make_supplier(supplier_name):
	if frappe.db.exists("Supplier", {"supplier_name": supplier_name}):
		return frappe.get_doc("Supplier", {"supplier_name": supplier_name})
	doc = frappe.new_doc("Supplier")
	doc.supplier_name = supplier_name
	doc.supplier_type = "Company"
	doc.supplier_group = frappe.db.get_value("Supplier Group", {"is_group": 0}, "name")
	doc.insert(ignore_permissions=True)
	return doc


def _make_address(title, link_doctype, link_name):
	doc = frappe.new_doc("Address")
	doc.address_title = title
	doc.address_type = "Billing"
	doc.address_line1 = "Test Street"
	doc.city = "Test City"
	doc.country = "India"
	doc.append("links", {"link_doctype": link_doctype, "link_name": link_name})
	doc.insert(ignore_permissions=True)
	return doc
