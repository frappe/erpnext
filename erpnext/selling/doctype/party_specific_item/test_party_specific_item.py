# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.controllers.queries import item_query
from erpnext.tests.utils import ERPNextTestSuite


def create_party_specific_item(**args):
	psi = frappe.new_doc("Party Specific Item")
	psi.party_type = args.get("party_type")
	psi.party = args.get("party")
	psi.restrict_based_on = args.get("restrict_based_on")
	psi.based_on_value = args.get("based_on_value")
	psi.insert()


class TestPartySpecificItem(ERPNextTestSuite):
	def test_item_query_for_customer(self):
		customer = "_Test Customer With Template"
		item = "_Test Item"

		create_party_specific_item(
			party_type="Customer",
			party=customer,
			restrict_based_on="Item",
			based_on_value=item,
		)
		filters = {"is_sales_item": 1, "customer": customer}
		items = item_query(
			doctype="Item", txt="", searchfield="name", start=0, page_len=20, filters=filters, as_dict=False
		)
		self.assertTrue(item in flatten(items))

	def test_item_query_for_supplier(self):
		supplier = "_Test Supplier With Template 1"
		item = "_Test Item Group"

		create_party_specific_item(
			party_type="Supplier",
			party=supplier,
			restrict_based_on="Item Group",
			based_on_value=item,
		)
		filters = {"supplier": supplier, "is_purchase_item": 1}
		items = item_query(
			doctype="Item", txt="", searchfield="name", start=0, page_len=20, filters=filters, as_dict=False
		)
		self.assertTrue(item in flatten(items))


def flatten(lst):
	result = []
	for item in lst:
		if isinstance(item, tuple):
			result.extend(flatten(item))
		else:
			result.append(item)
	return result
