# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.accounts.doctype.party_link.party_link import create_party_link
from erpnext.tests.utils import ERPNextTestSuite

CUSTOMER = "_Test Customer"
SUPPLIER = "_Test Supplier"


class TestPartyLink(ERPNextTestSuite):
	"""Party Link ties a Customer and a Supplier together as one underlying party.
	validate() constrains the primary role and blocks duplicate links."""

	def setUp(self):
		frappe.set_user("Administrator")

	def test_duplicate_link_throws(self):
		create_party_link("Customer", CUSTOMER, SUPPLIER)
		dup = frappe.new_doc("Party Link")
		dup.primary_role = "Customer"
		dup.primary_party = CUSTOMER
		dup.secondary_role = "Supplier"
		dup.secondary_party = SUPPLIER
		self.assertRaises(frappe.ValidationError, dup.insert)
