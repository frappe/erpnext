# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.utils import _create_bin
from erpnext.tests.assertions import assert_raises_with_savepoint
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
		with assert_raises_with_savepoint(self, frappe.UniqueValidationError):
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

	def test_repost_resets_bin_without_sle(self):
		"""A repost must zero the bin when the ledger is empty, e.g. after entries were deleted."""
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
		from erpnext.stock.stock_ledger import update_entries_after

		item_code = make_item().name
		warehouse = "_Test Warehouse - _TC"
		make_stock_entry(item_code=item_code, target=warehouse, qty=10, rate=100)

		# deleting a transaction with `delete_linked_ledger_entries` on drops its entries outright
		frappe.db.delete("Stock Ledger Entry", {"item_code": item_code, "warehouse": warehouse})

		update_entries_after(
			{
				"item_code": item_code,
				"warehouse": warehouse,
				"posting_date": "1900-01-01",
				"posting_time": "00:01",
			}
		)

		bin = frappe.get_doc("Bin", {"item_code": item_code, "warehouse": warehouse})
		self.assertEqual(bin.actual_qty, 0)
		self.assertEqual(bin.valuation_rate, 0)
		self.assertEqual(bin.stock_value, 0)

	def test_cancelling_last_entry_resets_bin(self):
		"""Cancelling the only voucher must clear stock value, not just quantity."""
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		item_code = make_item().name
		warehouse = "_Test Warehouse - _TC"
		se = make_stock_entry(item_code=item_code, target=warehouse, qty=10, rate=100)

		se.cancel()

		bin = frappe.get_doc("Bin", {"item_code": item_code, "warehouse": warehouse})
		self.assertEqual(bin.actual_qty, 0)
		self.assertEqual(bin.valuation_rate, 0)
		self.assertEqual(bin.stock_value, 0)

	def test_deleting_last_voucher_resets_bin(self):
		"""Deleting the only voucher wipes its ledger entries outright, the bin must still be cleared."""
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		item_code = make_item().name
		warehouse = "_Test Warehouse - _TC"
		delete_entries = frappe.get_single_value("Accounts Settings", "delete_linked_ledger_entries")
		frappe.db.set_single_value("Accounts Settings", "delete_linked_ledger_entries", 1)

		try:
			se = make_stock_entry(item_code=item_code, target=warehouse, qty=10, rate=100)
			se.cancel()
			frappe.delete_doc("Stock Entry", se.name, force=1)
		finally:
			frappe.db.set_single_value("Accounts Settings", "delete_linked_ledger_entries", delete_entries)

		bin = frappe.get_doc("Bin", {"item_code": item_code, "warehouse": warehouse})
		self.assertEqual(bin.actual_qty, 0)
		self.assertEqual(bin.valuation_rate, 0)
		self.assertEqual(bin.stock_value, 0)

	def test_index_exists(self):
		# has_index is db-agnostic; raw "SHOW INDEX" is MySQL-only and errors on Postgres
		if not frappe.db.has_index("tabBin", "unique_item_warehouse"):
			self.fail("Expected unique index on item-warehouse")
