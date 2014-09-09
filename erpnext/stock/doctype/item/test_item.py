# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import unittest
import frappe

from frappe.test_runner import make_test_records

test_ignore = ["BOM"]
test_dependencies = ["Warehouse"]

class TestItem(unittest.TestCase):
	def test_default_warehouse(self):
		from erpnext.stock.doctype.item.item import WarehouseNotSet
		item = frappe.copy_doc(test_records[0])
		item.is_stock_item = "Yes"
		item.default_warehouse = None
		self.assertRaises(WarehouseNotSet, item.insert)

	def test_get_item_details(self):
		from erpnext.stock.get_item_details import get_item_details
		to_check = {
			"item_code": "_Test Item",
			"item_name": "_Test Item",
			"description": "_Test Item",
			"warehouse": "_Test Warehouse - _TC",
			"income_account": "Sales - _TC",
			"expense_account": "_Test Account Cost for Goods Sold - _TC",
			"cost_center": "_Test Cost Center 2 - _TC",
			"qty": 1.0,
			"price_list_rate": 100.0,
			"base_price_list_rate": 0.0,
			"discount_percentage": 0.0,
			"rate": 0.0,
			"base_rate": 0.0,
			"amount": 0.0,
			"base_amount": 0.0,
			"batch_no": None,
			"item_tax_rate": '{}',
			"uom": "_Test UOM",
			"conversion_factor": 1.0,
		}

		make_test_records("Item Price")

		details = get_item_details({
			"item_code": "_Test Item",
			"company": "_Test Company",
			"price_list": "_Test Price List",
			"currency": "_Test Currency",
			"parenttype": "Sales Order",
			"conversion_rate": 1,
			"price_list_currency": "_Test Currency",
			"plc_conversion_rate": 1,
			"order_type": "Sales",
			"transaction_type": "selling"
		})

		for key, value in to_check.iteritems():
			self.assertEquals(value, details.get(key))

test_records = frappe.get_test_records('Item')
