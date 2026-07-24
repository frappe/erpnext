# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.stock_ledger_invariant_check.stock_ledger_invariant_check import execute
from erpnext.tests.utils import ERPNextTestSuite

WAREHOUSE = "Stores - _TC"
COMPANY = "_Test Company"
ITEM = "_Test Item"


class TestStockLedgerInvariantCheck(ERPNextTestSuite):
	def run_report(self, **extra):
		filters = frappe._dict({"company": COMPANY, "warehouse": WAREHOUSE})
		filters.update(extra)
		return execute(filters)[1]

	def make_movements(self) -> str:
		frappe.db.set_value("Item", ITEM, "valuation_method", "FIFO")
		make_stock_entry(item_code=ITEM, to_warehouse=WAREHOUSE, qty=10, rate=100, posting_date="2026-06-01")
		make_stock_entry(item_code=ITEM, to_warehouse=WAREHOUSE, qty=5, rate=120, posting_date="2026-06-02")
		make_stock_entry(item_code=ITEM, from_warehouse=WAREHOUSE, qty=4, rate=0, posting_date="2026-06-03")
		return ITEM

	def test_diagnostic_rows_have_no_discrepancy(self):
		item = self.make_movements()

		data = self.run_report(item_code=item)

		self.assertEqual(len(data), 3)
		for row in data:
			self.assertLess(abs(row.difference_in_qty), 0.01)
			self.assertLess(abs(row.fifo_qty_diff), 0.01)
			self.assertLess(abs(row.diff_value_diff), 0.01)

	def test_running_balance_matches(self):
		item = self.make_movements()

		data = self.run_report(item_code=item)

		self.assertEqual(data[-1].qty_after_transaction, 11)

	def test_show_incorrect_entries(self):
		item = self.make_movements()

		self.assertEqual(self.run_report(item_code=item, show_incorrect_entries=1), [])

		sle = frappe.get_last_doc(
			"Stock Ledger Entry", {"item_code": item, "warehouse": WAREHOUSE, "is_cancelled": 0}
		)
		frappe.db.set_value(
			"Stock Ledger Entry", sle.name, "qty_after_transaction", sle.qty_after_transaction + 5
		)

		data = self.run_report(item_code=item, show_incorrect_entries=1)
		self.assertEqual(len(data), 2)  # incorrect entry + one before it for context
		self.assertEqual(data[-1].name, sle.name)

	def test_batch_item_skips_fifo_queue_checks(self):
		from erpnext.stock.doctype.item.test_item import make_item

		item = make_item(
			properties={"has_batch_no": 1, "create_new_batch": 1, "batch_number_series": "SLIC-BAT-.####"}
		).name
		make_stock_entry(item_code=item, to_warehouse=WAREHOUSE, qty=10, rate=100)

		data = self.run_report(item_code=item)
		self.assertTrue(data)
		for row in data:
			self.assertIsNone(row.fifo_qty_diff)
			self.assertIsNone(row.fifo_value_diff)

		self.assertEqual(self.run_report(item_code=item, show_incorrect_entries=1), [])
