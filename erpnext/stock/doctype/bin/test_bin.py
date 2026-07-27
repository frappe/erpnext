# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.utils import _create_bin
from erpnext.tests.utils import ERPNextTestSuite


class TestBin(ERPNextTestSuite):
	def test_concurrent_inserts(self):
		"""Ensure no duplicates are possible in case of concurrent inserts"""
		item_code = "_TestConcurrentBin"
		make_item(item_code)
		warehouse = "_Test Warehouse - _TC"

		bin1 = frappe.get_doc(doctype="Bin", item_code=item_code, warehouse=warehouse)
		bin1.insert()

		bin2 = frappe.get_doc(doctype="Bin", item_code=item_code, warehouse=warehouse)
		with self.assertRaises(frappe.UniqueValidationError):
			bin2.insert()

		# util method should handle it
		bin = _create_bin(item_code, warehouse)
		self.assertEqual(bin.item_code, item_code)

	def test_recalculate_values(self):
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		item_code = make_item().name
		warehouse = "_Test Warehouse - _TC"
		make_stock_entry(item_code=item_code, target=warehouse, qty=10, rate=100)

		bin = frappe.get_doc("Bin", {"item_code": item_code, "warehouse": warehouse})
		bin.db_set({"actual_qty": 0, "valuation_rate": 0, "stock_value": 0})
		bin.reload()
		bin.recalculate_values()

		self.assertEqual(bin.actual_qty, 10)
		self.assertEqual(bin.valuation_rate, 100)
		self.assertEqual(bin.stock_value, 1000)

	def test_recalculate_values_without_sle(self):
		item_code = make_item().name
		warehouse = "_Test Warehouse - _TC"

		bin = _create_bin(item_code, warehouse)
		bin.db_set({"actual_qty": 5, "valuation_rate": 50, "stock_value": 250})
		bin.reload()
		bin.recalculate_values()

		self.assertEqual(bin.actual_qty, 0)
		self.assertEqual(bin.valuation_rate, 0)
		self.assertEqual(bin.stock_value, 0)

	def test_index_exists(self):
		indexes = frappe.db.sql("show index from tabBin where Non_unique = 0", as_dict=1)
		if not any(index.get("Key_name") == "unique_item_warehouse" for index in indexes):
			self.fail("Expected unique index on item-warehouse")
