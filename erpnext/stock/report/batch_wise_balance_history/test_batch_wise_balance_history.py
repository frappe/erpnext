# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.batch_wise_balance_history.batch_wise_balance_history import execute
from erpnext.tests.utils import ERPNextTestSuite

WH = "Stores - _TC"
# row indexes: 0 item, 1 name, 2 desc, 3 wh, 4 batch, 5 opening, 6 in, 7 out, 8 bal, 9 rate, 10 value, 11 uom


class TestBatchWiseBalanceHistory(ERPNextTestSuite):
	def make_batch_item(self):
		return make_item(
			properties={
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "BWB-.#####",
			}
		).name

	def run_report(self, item, from_date="2026-01-01", to_date="2026-12-31"):
		filters = frappe._dict(
			{"company": "_Test Company", "item_code": item, "from_date": from_date, "to_date": to_date}
		)
		return execute(filters)[1]

	def test_in_out_balance_and_valuation(self):
		item = self.make_batch_item()
		make_stock_entry(item_code=item, to_warehouse=WH, qty=10, rate=100, posting_date="2026-06-01")
		make_stock_entry(item_code=item, from_warehouse=WH, qty=4, posting_date="2026-06-02")

		(row,) = self.run_report(item)
		self.assertEqual(row[5], 0)  # opening
		self.assertEqual(row[6], 10)  # in
		self.assertEqual(row[7], 4)  # out
		self.assertEqual(row[8], 6)  # balance
		self.assertEqual(row[9], 100)  # valuation rate
		self.assertEqual(row[10], 600)  # balance value

	def test_opening_qty_from_prior_period(self):
		item = self.make_batch_item()
		make_stock_entry(item_code=item, to_warehouse=WH, qty=8, rate=50, posting_date="2025-12-01")

		(row,) = self.run_report(item)
		self.assertEqual(row[5], 8)  # opening carried from 2025
		self.assertEqual(row[6], 0)
		self.assertEqual(row[8], 8)  # balance
