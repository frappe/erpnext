# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe

from erpnext.controllers.queries import item_query

item_records = frappe.get_test_records('Item')
customer_records = frappe.get_test_records('Customer')
supplier_records = frappe.get_test_records('Supplier')

def create_party_specific_item(**args):
	psi = frappe.new_doc("Party Specific Item")
	psi.party_type = args.get('party_type')
	psi.party = args.get('party')
	psi.restrict_based_on = args.get('restrict_based_on')
	psi.based_on_value = args.get('based_on_value')
	psi.insert()

class TestPartySpecificItem(unittest.TestCase):
	def setUp(self):
		frappe.db.delete("Party Specific Item")
		frappe.db.delete("Item")
		frappe.db.delete("Customer")
		frappe.db.delete("Supplier")

		for i in range(5):
			frappe.get_doc(item_records[i]).insert()

		self.item = frappe.get_last_doc("Item")
		self.customer = frappe.get_doc(customer_records[0]).insert()
		self.supplier = frappe.get_doc(supplier_records[0]).insert()
		self.test_user = "test1@example.com"

	def test_item_query_for_customer(self):
		create_party_specific_item(party_type='Customer', party=self.customer.name, restrict_based_on='Item', based_on_value=self.item.name)
		filters = {'is_sales_item': 1, 'customer': self.customer.name}
		items = item_query(doctype= 'Item', txt= '', searchfield= 'name', start= 0, page_len= 20,filters=filters, as_dict= False)
		for item in items:
			self.assertEqual(item[0], self.item.name)

	def test_item_query_for_supplier(self):
		create_party_specific_item(party_type='Supplier', party=self.supplier.name, restrict_based_on='Item Group', based_on_value=self.item.item_group)
		filters = {'supplier': self.supplier.name, 'is_purchase_item': 1}
		items = item_query(doctype= 'Item', txt= '', searchfield= 'name', start= 0, page_len= 20,filters=filters, as_dict= False)
		for item in items:
			self.assertEqual(item[2], self.item.item_group)

	def tearDown(self):
		frappe.set_user("Administrator")
