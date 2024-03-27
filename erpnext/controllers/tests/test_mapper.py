import json
import unittest

import frappe
import frappe.utils
from frappe.model import mapper
from frappe.test_runner import make_test_records
from frappe.utils import add_months, nowdate


class TestMapper(unittest.TestCase):
	def test_map_docs(self):
		"""Test mapping of multiple source docs on a single target doc"""

		make_test_records("Item")
		items = ["_Test Item", "_Test Item 2", "_Test FG Item"]

		# Make source docs (quotations) and a target doc (sales order)
		qtn1, item_list_1 = self.make_quotation(items, "_Test Customer")
		qtn2, item_list_2 = self.make_quotation(items, "_Test Customer")
		so, item_list_3 = self.make_sales_order()

		# Map source docs to target with corresponding mapper method
		method = "erpnext.selling.doctype.quotation.quotation.make_sales_order"
		updated_so = mapper.map_docs(method, json.dumps([qtn1.name, qtn2.name]), so)

		# Assert that all inserted items are present in updated sales order
		src_items = item_list_1 + item_list_2 + item_list_3
		self.assertEqual(set(d for d in src_items), set(d.item_code for d in updated_so.items))

	def make_quotation(self, item_list, customer):
		qtn = frappe.get_doc(
			{
				"doctype": "Quotation",
				"quotation_to": "Customer",
				"party_name": customer,
				"order_type": "Sales",
				"transaction_date": nowdate(),
				"valid_till": add_months(nowdate(), 1),
			}
		)
		for item in item_list:
			qtn.append("items", {"qty": "2", "item_code": item})

		qtn.submit()
		return qtn, item_list

	def make_sales_order(self):
		item = frappe.get_doc(
			{
				"base_amount": 1000.0,
				"base_rate": 100.0,
				"description": "CPU",
				"doctype": "Sales Order Item",
				"item_code": "_Test Item",
				"item_name": "CPU",
				"parentfield": "items",
				"qty": 10.0,
				"rate": 100.0,
				"warehouse": "_Test Warehouse - _TC",
				"stock_uom": "_Test UOM",
				"conversion_factor": 1.0,
				"uom": "_Test UOM",
			}
		)
		so = frappe.get_doc(frappe.get_test_records("Sales Order")[0])
		so.insert(ignore_permissions=True)
		return so, [item.item_code]
