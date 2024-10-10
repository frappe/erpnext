# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase

from erpnext.controllers.queries import item_query

EXTRA_TEST_RECORD_DEPENDENCIES = ["Item", "Customer", "Supplier"]


def create_party_specific_item(**args):
	psi = frappe.new_doc("Party Specific Item")
	psi.party_type = args.get("party_type")
	psi.party = args.get("party")
	psi.restrict_based_on = args.get("restrict_based_on")
	psi.based_on_value = args.get("based_on_value")
	psi.insert()


class UnitTestPartySpecificItem(UnitTestCase):
	"""
	Unit tests for PartySpecificItem.
	Use this class for testing individual functions and methods.
	"""

	pass


class TestPartySpecificItem(IntegrationTestCase):
	def setUp(self):
		self.customer = frappe.get_last_doc("Customer")
		self.supplier = frappe.get_last_doc("Supplier")
		self.item = frappe.get_last_doc("Item")

	def test_item_query_for_customer(self):
		create_party_specific_item(
			party_type="Customer",
			party=self.customer.name,
			restrict_based_on="Item",
			based_on_value=self.item.name,
		)
		filters = {"is_sales_item": 1, "customer": self.customer.name}
		items = item_query(
			doctype="Item", txt="", searchfield="name", start=0, page_len=20, filters=filters, as_dict=False
		)
		for item in items:
			self.assertEqual(item[0], self.item.name)

	def test_item_query_for_supplier(self):
		create_party_specific_item(
			party_type="Supplier",
			party=self.supplier.name,
			restrict_based_on="Item Group",
			based_on_value=self.item.item_group,
		)
		filters = {"supplier": self.supplier.name, "is_purchase_item": 1}
		items = item_query(
			doctype="Item", txt="", searchfield="name", start=0, page_len=20, filters=filters, as_dict=False
		)
		for item in items:
			self.assertEqual(item[2], self.item.item_group)
