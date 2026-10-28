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

	def test_secondary_party_in_two_links_throws(self):
		create_party_link("Customer", CUSTOMER, SUPPLIER)
		link2 = frappe.new_doc("Party Link")
		link2.primary_role = "Customer"
		link2.primary_party = "_Test Customer 1"
		link2.secondary_role = "Supplier"
		link2.secondary_party = SUPPLIER
		self.assertRaisesRegex(frappe.ValidationError, "already linked with another", link2.insert)

	def test_secondary_role_must_be_the_other_role(self):
		doc = frappe.new_doc("Party Link")
		doc.primary_role = "Customer"
		doc.primary_party = CUSTOMER
		doc.secondary_role = "Customer"
		doc.secondary_party = "_Test Customer 1"
		self.assertRaisesRegex(frappe.ValidationError, "secondary role must be Supplier", doc.insert)

	def test_existing_link_can_be_saved(self):
		link = create_party_link("Customer", CUSTOMER, SUPPLIER)
		link.reload()
		link.save()

	def test_same_name_customer_and_supplier(self):
		from erpnext.accounts.doctype.opening_invoice_creation_tool.test_opening_invoice_creation_tool import (
			make_customer,
		)
		from erpnext.buying.doctype.supplier.test_supplier import create_supplier

		customer = make_customer(customer="_Test Party Link Same Name")
		supplier = create_supplier(supplier_name="_Test Party Link Same Name").name
		create_party_link("Customer", CUSTOMER, supplier)
		# the supplier of the same name is a secondary party, not the customer
		link = create_party_link("Customer", customer, SUPPLIER)
		self.assertTrue(frappe.db.exists("Party Link", link.name))

	@ERPNextTestSuite.change_settings("Accounts Settings", {"enable_common_party_accounting": 1})
	def test_common_party_journal_cancelled_after_setup_change(self):
		from erpnext.accounts.doctype.opening_invoice_creation_tool.test_opening_invoice_creation_tool import (
			make_customer,
		)
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
		from erpnext.buying.doctype.supplier.test_supplier import create_supplier

		customer = make_customer(customer="_Test Party Link Cancel")
		supplier = create_supplier(supplier_name="_Test Party Link Cancel").name
		link = create_party_link("Supplier", supplier, customer)

		def common_party_journal(si):
			return frappe.get_all(
				"Journal Entry Account",
				filters={"reference_type": "Sales Invoice", "reference_name": si.name},
				pluck="parent",
			)[0]

		# the setting is turned off before the cancel
		si = create_sales_invoice(customer=customer, parent_cost_center="_Test Cost Center - _TC")
		journal = common_party_journal(si)
		frappe.db.set_single_value("Accounts Settings", "enable_common_party_accounting", 0)
		si.cancel()
		self.assertEqual(frappe.db.get_value("Journal Entry", journal, "docstatus"), 2)

		# the Party Link is deleted before the cancel
		frappe.db.set_single_value("Accounts Settings", "enable_common_party_accounting", 1)
		si = create_sales_invoice(customer=customer, parent_cost_center="_Test Cost Center - _TC")
		journal = common_party_journal(si)
		link.delete()
		si.cancel()
		self.assertEqual(frappe.db.get_value("Journal Entry", journal, "docstatus"), 2)
