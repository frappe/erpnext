# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.item_wise_consumption.item_wise_consumption import execute
from erpnext.tests.utils import ERPNextTestSuite

WH = "Stores - _TC"
# row: 0 item, 1 name, 2 desc, 3 uom, 4 consumed_qty, 5 consumed_amt, 6 delivered_qty,
#      7 delivered_amt, 8 total_qty, 9 total_amt, 10 suppliers


class TestItemWiseConsumption(ERPNextTestSuite):
	def run_report(self, **extra):
		filters = frappe._dict(
			{"company": "_Test Company", "from_date": "2026-01-01", "to_date": "2026-12-31", **extra}
		)
		return execute(filters)[1]

	def test_consumed_vs_delivered_split(self):
		# a uniquely-named item guarantees no residual stock/consumption from other
		# tests leaks in -- the report aggregates an item across all warehouses.
		item = make_item(properties={"is_stock_item": 1}).name
		# purchase receipt gives the supplier mapping and stocks the item
		make_purchase_receipt(
			item_code=item,
			qty=10,
			rate=100,
			warehouse=WH,
			supplier="_Test Supplier",
			posting_date="2026-06-01",
		)
		# a material issue counts as "consumed", a delivery note counts as "delivered"
		make_stock_entry(item_code=item, from_warehouse=WH, qty=4, posting_date="2026-06-02")
		create_delivery_note(item_code=item, qty=3, warehouse=WH, posting_date="2026-06-03")

		row = next(r for r in self.run_report() if r[0] == item)
		self.assertEqual(row[4], 4)  # consumed qty
		self.assertEqual(row[5], 400)  # consumed amount
		self.assertEqual(row[6], 3)  # delivered qty
		self.assertEqual(row[7], 300)  # delivered amount
		self.assertEqual(row[8], 7)  # total qty = consumed + delivered
		self.assertEqual(row[9], 700)  # total amount = consumed + delivered amount
		self.assertEqual(row[9], row[5] + row[7])  # total aggregates the two amounts
		self.assertIn("_Test Supplier", row[10])
