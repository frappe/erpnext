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


def create_supplier(supplier_name):
	if frappe.db.exists("Supplier", supplier_name):
		return frappe.get_doc("Supplier", supplier_name)

	return frappe.get_doc(
		{
			"doctype": "Supplier",
			"supplier_name": supplier_name,
			"supplier_group": "Services",
			"supplier_type": "Company",
		}
	).insert()


def create_item(item_code):
	if frappe.db.exists("Item", item_code):
		return frappe.get_doc("Item", item_code)

	return frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": item_code,
			"item_name": item_code,
			"description": item_code,
			"item_group": "Products",
			"is_purchase_item": 1,
		}
	).insert()


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
		self.assertIn(item, flatten(items))

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
		self.assertIn(item, flatten(items))

	def test_item_query_for_supplier_with_item_restricted_to_multiple_suppliers(self):
		item = f"Party Specific Item {frappe.generate_hash(length=8)}"
		supplier1 = f"Party Specific Supplier {frappe.generate_hash(length=8)}"
		supplier2 = f"Party Specific Supplier {frappe.generate_hash(length=8)}"

		create_item(item)
		create_supplier(supplier1)
		create_supplier(supplier2)

		for supplier in (supplier1, supplier2):
			create_party_specific_item(
				party_type="Supplier",
				party=supplier,
				restrict_based_on="Item",
				based_on_value=item,
			)

		items = item_query(
			doctype="Item",
			txt=item,
			searchfield="name",
			start=0,
			page_len=20,
			filters={"supplier": supplier1, "is_purchase_item": 1},
			as_dict=False,
		)
		self.assertIn(item, flatten(items))

	def test_party_group(self):
		customer = "_Test Customer With Template"
		item = "_Test Item"
		frappe.set_value("Customer", customer, "customer_group", "Government")

		create_party_specific_item(
			party_type="Customer Group",
			party="Government",
			restrict_based_on="Item",
			based_on_value=item,
		)
		filters = {"is_sales_item": 1, "customer": customer}
		items = item_query(
			doctype="Item", txt="", searchfield="name", start=0, page_len=20, filters=filters, as_dict=False
		)
		self.assertIn(item, flatten(items))


def flatten(lst):
	result = []
	for item in lst:
		if isinstance(item, tuple):
			result.extend(flatten(item))
		else:
			result.append(item)
	return result
