from __future__ import unicode_literals
import unittest
import frappe

import random, json
import frappe.utils
from frappe.utils import nowdate
from frappe.model import mapper
from frappe.test_runner import make_test_records

class TestMapper(unittest.TestCase):
	def test_map_docs(self):
		'''Test mapping of multiple source docs on a single target doc'''

		make_test_records("Item")
		items = frappe.get_all("Item", fields = ["name", "item_code"], filters = {'is_sales_item': 1, 'has_variants': 0})
		customers = frappe.get_all("Customer")
		if items and customers:
			# Make source docs (quotations) and a target doc (sales order)
			customer = random.choice(customers).name
			qtn1, item_list_1 = self.make_quotation(items, customer)
			qtn2, item_list_2 = self.make_quotation(items, customer)
			so, item_list_3 = self.make_sales_order()

		# Map source docs to target with corresponding mapper method
		method = "erpnext.selling.doctype.quotation.quotation.make_sales_order"
		updated_so = mapper.map_docs(method, json.dumps([qtn1.name, qtn2.name]), so)

		# Assert that all inserted items are present in updated sales order
		src_items = item_list_1 + item_list_2 + item_list_3
		self.assertEqual(set([d.item_code for d in src_items]),
			set([d.item_code for d in updated_so.items]))

	def get_random_items(self, items, limit):
		'''Get a number of random items from a list of given items'''
		random_items = []
		for i in range(0, limit):
			random_items.append(random.choice(items))
		return random_items

	def make_quotation(self, items, customer):
		item_list = self.get_random_items(items, 3)
		qtn = frappe.get_doc({
			"doctype": "Quotation",
			"quotation_to": "Customer",
			"customer": customer,
			"order_type": "Sales"
		})
		for item in item_list:
			qtn.append("items", {"qty": "2", "item_code": item.item_code})

		qtn.submit()
		return qtn, item_list

	def make_sales_order(self):
		item = frappe.get_doc({
			"base_amount": 1000.0,
			"base_rate": 100.0,
			"description": "CPU",
			"doctype": "Sales Order Item",
			"item_code": "_Test Item Home Desktop 100",
			"item_name": "CPU",
			"parentfield": "items",
			"qty": 10.0,
			"rate": 100.0,
			"warehouse": "_Test Warehouse - _TC",
			"stock_uom": "_Test UOM",
			"conversion_factor": 1.0,
			"uom": "_Test UOM"
		})
		so = frappe.get_doc(frappe.get_test_records('Sales Order')[0])
		so.insert(ignore_permissions=True)
		return so, [item]
