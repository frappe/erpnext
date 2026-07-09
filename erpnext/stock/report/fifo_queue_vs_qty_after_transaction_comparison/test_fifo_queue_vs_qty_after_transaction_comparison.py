# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.fifo_queue_vs_qty_after_transaction_comparison.fifo_queue_vs_qty_after_transaction_comparison import (
	execute,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestFifoQueueVsQtyAfterTransactionComparison(ERPNextTestSuite):
	def run_report(self, filters: dict) -> list:
		return execute(frappe._dict(filters))[1]

	def test_healthy_fifo_item_no_mismatch(self):
		item = "_Test Item"
		warehouse = "Stores - _TC"
		frappe.db.set_value("Item", item, "valuation_method", "FIFO")

		make_stock_entry(item_code=item, to_warehouse=warehouse, qty=10, rate=100, posting_date="2026-06-01")
		make_stock_entry(item_code=item, to_warehouse=warehouse, qty=5, rate=120, posting_date="2026-06-01")
		make_stock_entry(item_code=item, from_warehouse=warehouse, qty=4, posting_date="2026-06-02")

		data = self.run_report({"company": "_Test Company", "item_code": item, "warehouse": warehouse})

		item_codes = [row.get("item_code") for row in data if row]
		self.assertNotIn(item, item_codes)

	def test_queue_out_of_sync_is_flagged(self):
		item = "_Test Item 2"
		warehouse = "Stores - _TC"
		frappe.db.set_value("Item", item, "valuation_method", "FIFO")

		entry = make_stock_entry(
			item_code=item, to_warehouse=warehouse, qty=10, rate=100, posting_date="2026-06-01"
		)
		sle = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_no": entry.name, "item_code": item, "warehouse": warehouse},
			"name",
		)

		# corrupt the running balance so it no longer matches the FIFO queue (the queue holds 10,
		# but the stored qty_after_transaction now claims 7)
		frappe.db.set_value("Stock Ledger Entry", sle, "qty_after_transaction", 7, update_modified=False)

		data = self.run_report({"company": "_Test Company", "item_code": item, "warehouse": warehouse})

		flagged = {row.get("name") for row in data if row}
		self.assertIn(sle, flagged)

	def test_requires_a_filter(self):
		with self.assertRaises(frappe.ValidationError):
			self.run_report({"company": "_Test Company"})
