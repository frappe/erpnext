# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.accounts.doctype.party_link.party_link import create_party_link
from erpnext.tests.utils import ERPNextTestSuite

CUSTOMER = "_Test Customer"
SUPPLIER = "_Test Supplier"
SUPPLIER_2 = "_Test Supplier 1"


class TestPartyLink(ERPNextTestSuite):
	"""Party Link ties a Customer and a Supplier together as one underlying party.
	validate() constrains the primary role and blocks duplicate links."""

	def setUp(self):
		frappe.set_user("Administrator")

	def test_create_party_link_with_customer_primary(self):
		link = create_party_link("Customer", CUSTOMER, SUPPLIER)
		self.assertEqual(link.primary_role, "Customer")
		self.assertEqual(link.secondary_role, "Supplier")
		self.assertEqual(link.primary_party, CUSTOMER)
		self.assertEqual(link.secondary_party, SUPPLIER)
		self.assertTrue(frappe.db.exists("Party Link", link.name))

	def test_create_party_link_with_supplier_primary(self):
		link = create_party_link("Supplier", SUPPLIER, CUSTOMER)
		self.assertEqual(link.primary_role, "Supplier")
		self.assertEqual(link.secondary_role, "Customer")
		self.assertEqual(link.primary_party, SUPPLIER)
		self.assertEqual(link.secondary_party, CUSTOMER)
		self.assertTrue(frappe.db.exists("Party Link", link.name))

	def test_primary_role_must_be_customer_or_supplier(self):
		doc = frappe.new_doc("Party Link")
		doc.primary_role = "Employee"
		doc.primary_party = CUSTOMER
		doc.secondary_role = "Supplier"
		doc.secondary_party = SUPPLIER
		# validate() alone isolates the role rule from the dynamic-link checks
		self.assertRaises(frappe.ValidationError, doc.validate)

	def test_duplicate_link_throws(self):
		create_party_link("Customer", CUSTOMER, SUPPLIER)
		dup = frappe.new_doc("Party Link")
		dup.primary_role = "Customer"
		dup.primary_party = CUSTOMER
		dup.secondary_role = "Supplier"
		dup.secondary_party = SUPPLIER
		self.assertRaises(frappe.ValidationError, dup.insert)

	def test_party_can_wrongly_be_primary_in_two_links(self):
		# SUSPECTED BUG: the uniqueness checks are asymmetric - a party already a
		# *primary* in another link isn't blocked, so one customer can be linked to two
		# different suppliers, breaking the 1:1 mapping. Locking the current (wrong)
		# behaviour so a fix that blocks primary reuse trips this test.
		create_party_link("Customer", CUSTOMER, SUPPLIER)
		link2 = frappe.new_doc("Party Link")
		link2.primary_role = "Customer"
		link2.primary_party = CUSTOMER
		link2.secondary_role = "Supplier"
		link2.secondary_party = SUPPLIER_2
		link2.insert()
		self.assertTrue(frappe.db.exists("Party Link", link2.name))
