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
		frappe.db.savepoint("dup_bin")
		with self.assertRaises(frappe.UniqueValidationError):
			bin2.insert()
		frappe.db.rollback(save_point="dup_bin")  # preserve transaction in postgres

		# util method should handle it
		bin = _create_bin(item_code, warehouse)
		self.assertEqual(bin.item_code, item_code)

	def test_index_exists(self):
		# has_index is db-agnostic; raw "SHOW INDEX" is MySQL-only and errors on Postgres
		if not frappe.db.has_index("tabBin", "unique_item_warehouse"):
			self.fail("Expected unique index on item-warehouse")
