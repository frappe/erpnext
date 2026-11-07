# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.fifo_queue_vs_qty_after_transaction_comparison.fifo_queue_vs_qty_after_transaction_comparison import (
	execute,
)


class TestFifoQueueVsQtyAfterTransactionComparison(FrappeTestCase):
	def run_report(self, filters: dict) -> list:
		return execute(frappe._dict(filters))[1]

	def test_items_without_a_queue_are_not_flagged(self):
		from erpnext.stock.doctype.item.test_item import make_item

		item = make_item(properties={"is_stock_item": 1, "valuation_method": "Moving Average"}).name
		make_stock_entry(item_code=item, to_warehouse="Stores - _TC", qty=10, rate=100)

		data = self.run_report({"company": "_Test Company", "item_code": item})

		self.assertEqual([row for row in data if row], [])

	def test_from_date_applies_with_to_date(self):
		from erpnext.stock.doctype.item.test_item import make_item

		item = make_item(properties={"is_stock_item": 1, "valuation_method": "FIFO"}).name
		entry = make_stock_entry(
			item_code=item, to_warehouse="Stores - _TC", qty=10, rate=100, posting_date="2026-06-01"
		)
		make_stock_entry(
			item_code=item, to_warehouse="Stores - _TC", qty=5, rate=100, posting_date="2026-06-20"
		)
		sle = frappe.db.get_value("Stock Ledger Entry", {"voucher_no": entry.name}, "name")
		frappe.db.set_value("Stock Ledger Entry", sle, "qty_after_transaction", 7, update_modified=False)

		data = self.run_report(
			{
				"company": "_Test Company",
				"item_code": item,
				"from_date": "2026-06-10",
				"to_date": "2026-06-30",
			}
		)

		self.assertEqual([row for row in data if row], [])

	def test_wrong_fifo_entry_is_reported(self):
		from erpnext.stock.doctype.item.test_item import make_item

		item = make_item(properties={"is_stock_item": 1, "valuation_method": "FIFO"}).name
		make_stock_entry(
			item_code=item, to_warehouse="Stores - _TC", qty=10, rate=100, posting_date="2026-06-01"
		)
		entry = make_stock_entry(
			item_code=item, to_warehouse="Stores - _TC", qty=5, rate=100, posting_date="2026-06-20"
		)
		sle = frappe.db.get_value("Stock Ledger Entry", {"voucher_no": entry.name}, "name")
		frappe.db.set_value("Stock Ledger Entry", sle, "qty_after_transaction", 12, update_modified=False)

		for filters in (
			{"item_code": item},
			{"item_code": item, "from_date": "2026-06-01", "to_date": "2026-06-30"},
			{"warehouse": "Stores - _TC", "from_date": "2026-06-20", "to_date": "2026-06-20"},
		):
			data = self.run_report({"company": "_Test Company", **filters})
			self.assertIn(sle, [row.get("name") for row in data if row])
