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

	def test_multi_item_opening_balance_with_and_without_transactions(self):
		item_a = "_Test Item"
		item_b = "_Test Item 2"
		self.make_movements(
			item_a,
			[
				{
					"qty": 10,
					"to_warehouse": WAREHOUSE,
					"basic_rate": 100,
					"posting_date": add_days(today(), -10),
				}
			],
		)
		self.make_movements(
			item_b,
			[{"qty": 5, "to_warehouse": WAREHOUSE, "basic_rate": 50, "posting_date": add_days(today(), -10)}],
		)
		self.make_movements(
			item_a,
			[{"qty": 2, "from_warehouse": WAREHOUSE, "posting_date": today()}],
		)

		filters = frappe._dict(
			company="_Test Company",
			from_date=add_days(today(), -5),
			to_date=today(),
			item_code=[item_a, item_b],
			warehouse=WAREHOUSE,
		)
		columns, rows = execute(filters)

		opening_rows = [row for row in rows if row.get("item_code") == "'Opening'"]
		self.assertEqual(len(opening_rows), 1)
		self.assertEqual(opening_rows[0]["qty_after_transaction"], 15)

	def test_multi_warehouse_opening_balance_aggregation(self):
		item = "_Test Item"
		warehouse_1 = "Stores - _TC"
		warehouse_2 = "Finished Goods - _TC"

		self.make_movements(
			item,
			[
				{
					"qty": 10,
					"to_warehouse": warehouse_1,
					"basic_rate": 100,
					"posting_date": add_days(today(), -10),
				},
				{
					"qty": 20,
					"to_warehouse": warehouse_2,
					"basic_rate": 100,
					"posting_date": add_days(today(), -10),
				},
			],
		)

		filters = frappe._dict(
			company="_Test Company",
			from_date=add_days(today(), -5),
			to_date=today(),
			item_code=[item],
			warehouse=[warehouse_1, warehouse_2],
		)
		columns, rows = execute(filters)

		opening_rows = [row for row in rows if row.get("item_code") == "'Opening'"]
		self.assertEqual(len(opening_rows), 1)
		self.assertEqual(opening_rows[0]["qty_after_transaction"], 30)

	def test_opening_stock_reconciliation_on_from_date_non_midnight_time(self):
		from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import (
			create_stock_reconciliation,
		)

		item = "_Test Item"
		from_date = today()

		sr = create_stock_reconciliation(
			item_code=item,
			warehouse=WAREHOUSE,
			qty=25,
			rate=100,
			posting_date=from_date,
			posting_time="10:30:00",
			purpose="Opening Stock",
			do_not_submit=False,
		)

		filters = frappe._dict(
			company="_Test Company",
			from_date=from_date,
			to_date=from_date,
			item_code=[item],
			warehouse=WAREHOUSE,
		)
		columns, rows = execute(filters)

		opening_rows = [row for row in rows if row.get("item_code") == "'Opening'"]
		self.assertEqual(len(opening_rows), 1)
		self.assertEqual(opening_rows[0]["qty_after_transaction"], 25)

		# Ensure the Opening Stock Reconciliation is not duplicated in detail transaction rows
		reco_rows = [row for row in rows if row.get("voucher_no") == sr.name]
		self.assertEqual(len(reco_rows), 0)

	def test_backdated_sle_independent_maxima_handling(self):
		item = "_Test Item"
		# Entry 1: Later posting date (2026-07-20), created first
		self.make_movements(
			item,
			[
				{
					"qty": 10,
					"to_warehouse": WAREHOUSE,
					"basic_rate": 100,
					"posting_date": add_days(today(), -10),
				}
			],
		)
		# Entry 2: Backdated posting date (2026-07-15), created LATER
		self.make_movements(
			item,
			[
				{
					"qty": 5,
					"to_warehouse": WAREHOUSE,
					"basic_rate": 100,
					"posting_date": add_days(today(), -15),
				}
			],
		)

		filters = frappe._dict(
			company="_Test Company",
			from_date=add_days(today(), -5),
			to_date=today(),
			item_code=[item],
			warehouse=WAREHOUSE,
		)
		columns, rows = execute(filters)

		opening_rows = [row for row in rows if row.get("item_code") == "'Opening'"]
		self.assertEqual(len(opening_rows), 1)
		# Should correctly pick the latest posting date entry (15 Qty) despite backdated creation order
		self.assertEqual(opening_rows[0]["qty_after_transaction"], 15)

	def test_filtered_opening_balance_does_not_pick_excluded_creation_entry(self):
		item = "_Test Item"
		posting_date = add_days(today(), -10)
		posting_time = "09:00:00"

		included_entry = make_stock_entry(
			item_code=item,
			qty=10,
			to_warehouse=WAREHOUSE,
			basic_rate=100,
			posting_date=posting_date,
			posting_time=posting_time,
		)
		make_stock_entry(
			item_code=item,
			qty=50,
			to_warehouse=WAREHOUSE,
			basic_rate=100,
			posting_date=posting_date,
			posting_time=posting_time,
		)

		filters = frappe._dict(
			company="_Test Company",
			from_date=add_days(today(), -5),
			to_date=today(),
			item_code=[item],
			warehouse=WAREHOUSE,
			voucher_no=included_entry.name,
		)
		columns, rows = execute(filters)

		opening_rows = [row for row in rows if row.get("item_code") == "'Opening'"]
		self.assertEqual(len(opening_rows), 1)
		self.assertEqual(opening_rows[0]["qty_after_transaction"], 10)

	def test_tied_creation_terminal_sle_is_not_summed_twice(self):
		item = "_Test Item"
		posting_date = add_days(today(), -10)
		posting_time = "09:00:00"

		stock_entry_1 = make_stock_entry(
			item_code=item,
			qty=10,
			to_warehouse=WAREHOUSE,
			basic_rate=100,
			posting_date=posting_date,
			posting_time=posting_time,
		)
		stock_entry_2 = make_stock_entry(
			item_code=item,
			qty=5,
			to_warehouse=WAREHOUSE,
			basic_rate=100,
			posting_date=posting_date,
			posting_time=posting_time,
		)

		sle_rows = frappe.get_all(
			"Stock Ledger Entry",
			filters={
				"voucher_type": "Stock Entry",
				"voucher_no": ("in", [stock_entry_1.name, stock_entry_2.name]),
				"item_code": item,
				"warehouse": WAREHOUSE,
				"is_cancelled": 0,
			},
			fields=["name", "qty_after_transaction"],
			order_by="name desc",
		)
		self.assertEqual(len(sle_rows), 2)

		for sle in sle_rows:
			frappe.db.set_value(
				"Stock Ledger Entry",
				sle.name,
				"creation",
				"2026-01-01 00:00:00.000000",
				update_modified=False,
			)

		filters = frappe._dict(
			company="_Test Company",
			from_date=add_days(today(), -5),
			to_date=today(),
			item_code=[item],
			warehouse=WAREHOUSE,
		)
		columns, rows = execute(filters)

		opening_rows = [row for row in rows if row.get("item_code") == "'Opening'"]
		self.assertEqual(len(opening_rows), 1)
		self.assertEqual(opening_rows[0]["qty_after_transaction"], sle_rows[0].qty_after_transaction)
		self.assertNotEqual(
			opening_rows[0]["qty_after_transaction"],
			sum(sle.qty_after_transaction for sle in sle_rows),
		)
