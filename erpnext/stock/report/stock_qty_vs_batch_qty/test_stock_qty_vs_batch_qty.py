# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.stock_qty_vs_batch_qty.stock_qty_vs_batch_qty import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestStockQtyVsBatchQty(ERPNextTestSuite):
	def run_report(self, **extra):
		return execute(frappe._dict({"company": "_Test Company", **extra}))[1]

	def make_batch_item(self):
		return make_item(
			properties={
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "SQB-.#####",
			}
		).name

	def rows_for_item(self, data, item):
		return [row for row in data if row["item_code"] == item]

	def test_stock_qty_matches_batch_qty(self):
		item = self.make_batch_item()
		make_stock_entry(
			item_code=item,
			to_warehouse="_Test Warehouse - _TC",
			qty=10,
			rate=100,
			posting_date="2026-06-01",
		)

		# The report only lists batches where stock qty and batch qty differ.
		# A healthy item has difference == 0, so it must be absent from results.
		data = self.run_report(item=item)
		self.assertEqual(self.rows_for_item(data, item), [])

	def test_mismatch_reports_difference(self):
		item = self.make_batch_item()
		make_stock_entry(
			item_code=item,
			to_warehouse="_Test Warehouse - _TC",
			qty=10,
			rate=100,
			posting_date="2026-06-01",
		)
		batch_no = frappe.db.get_value("Batch", {"item": item}, "name")
		self.assertTrue(batch_no)

		# Corrupt the stored batch qty so it no longer matches actual stock qty (10).
		frappe.db.set_value("Batch", batch_no, "batch_qty", 7)

		data = self.run_report(item=item, batch=batch_no)
		rows = self.rows_for_item(data, item)
		self.assertEqual(len(rows), 1)

		row = rows[0]
		self.assertEqual(row["batch"], batch_no)
		self.assertEqual(row["batch_qty"], 7)
		self.assertEqual(row["stock_qty"], 10)
		self.assertEqual(row["difference"], 3)
