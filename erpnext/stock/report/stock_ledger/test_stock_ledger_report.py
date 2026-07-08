# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import add_days, today

from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.stock_ledger.stock_ledger import execute
from erpnext.tests.utils import ERPNextTestSuite

WAREHOUSE = "Stores - _TC"


class TestStockLedgerReport(ERPNextTestSuite):
	"""Correctness tests for the Stock Ledger report.

	A shared `make_movements`/`run` pair keeps each test small without persisting
	any data: movements are created per test and rolled back, while the report runs
	read-only. Tests reuse bootstrap items and transact in `Stores - _TC`, which
	starts clean (zero balance) for these items.
	"""

	def make_movements(self, item_code, movements):
		for movement in movements:
			make_stock_entry(item_code=item_code, **movement)

	def run_report(self, item_code, from_date=None, to_date=None):
		filters = frappe._dict(
			company="_Test Company",
			from_date=from_date or add_days(today(), -1),
			to_date=to_date or today(),
			item_code=[item_code],
			warehouse=WAREHOUSE,
		)
		return list(execute(filters)[1])

	def test_in_out_quantities_and_running_balance(self):
		item = "_Test Item"
		self.make_movements(
			item,
			[
				{"qty": 10, "to_warehouse": WAREHOUSE, "basic_rate": 100},
				{"qty": 4, "from_warehouse": WAREHOUSE},
			],
		)

		rows = self.run_report(item)
		receipt = next(row for row in rows if row.get("in_qty"))
		issue = next(row for row in rows if row.get("out_qty"))

		self.assertEqual(receipt["in_qty"], 10)
		self.assertEqual(receipt["qty_after_transaction"], 10)
		self.assertEqual(issue["out_qty"], -4)
		self.assertEqual(issue["qty_after_transaction"], 6)

	def test_opening_balance_reflects_movements_before_from_date(self):
		item = "_Test Item"
		self.make_movements(
			item,
			[
				{
					"qty": 10,
					"to_warehouse": WAREHOUSE,
					"basic_rate": 100,
					"posting_date": add_days(today(), -10),
				},
				{"qty": 4, "from_warehouse": WAREHOUSE, "posting_date": today()},
			],
		)

		rows = self.run_report(item, from_date=add_days(today(), -5), to_date=today())

		# the receipt predates the range, so it surfaces as the opening balance
		self.assertEqual(rows[0]["item_code"], "'Opening'")
		self.assertEqual(rows[0]["qty_after_transaction"], 10)

		# the in-range issue draws down from the opening balance
		issue = next(row for row in rows if row.get("out_qty"))
		self.assertEqual(issue["qty_after_transaction"], 6)

	def test_filters_to_requested_item_only(self):
		item_a = "_Test Item"
		item_b = "_Test Item 2"
		self.make_movements(item_a, [{"qty": 5, "to_warehouse": WAREHOUSE, "basic_rate": 100}])
		self.make_movements(item_b, [{"qty": 7, "to_warehouse": WAREHOUSE, "basic_rate": 100}])

		rows = self.run_report(item_a)
		item_codes = {row["item_code"] for row in rows if row.get("voucher_no")}
		self.assertEqual(item_codes, {item_a})
