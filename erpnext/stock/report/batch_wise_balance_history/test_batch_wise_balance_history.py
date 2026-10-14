# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import today

from erpnext.selling.doctype.sales_order.mapper import make_delivery_note
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.doctype.stock_reconciliation.stock_reconciliation import get_itemwise_batch
from erpnext.stock.report.batch_wise_balance_history.batch_wise_balance_history import execute
from erpnext.tests.utils import ERPNextTestSuite

WH = "Stores - _TC"


class TestBatchWiseBalanceHistory(ERPNextTestSuite):
	def make_batch_item(self, **properties):
		return make_item(
			properties={
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "BWB-.#####",
				**properties,
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
		self.assertEqual(row.opening_qty, 0)
		self.assertEqual(row.in_qty, 10)
		self.assertEqual(row.out_qty, 4)
		self.assertEqual(row.balance_qty, 6)
		self.assertEqual(row.valuation_rate, 100)
		self.assertEqual(row.balance_value, 600)

	def test_pooled_batches_use_warehouse_rate(self):
		frappe.db.set_single_value("Stock Settings", "do_not_use_batchwise_valuation", 1)
		item = self.make_batch_item(valuation_method="Moving Average")
		make_stock_entry(item_code=item, to_warehouse=WH, qty=10, rate=100, posting_date="2026-06-01")
		make_stock_entry(item_code=item, to_warehouse=WH, qty=10, rate=300, posting_date="2026-06-02")
		first_batch = frappe.get_all("Batch", {"item": item}, pluck="name", order_by="creation")[0]
		make_stock_entry(
			item_code=item, from_warehouse=WH, qty=5, batch_no=first_batch, posting_date="2026-06-03"
		)
		make_stock_entry(item_code=item, to_warehouse=WH, qty=5, rate=600, posting_date="2026-06-04")

		rows = self.run_report(item, to_date="2026-06-03")
		self.assertEqual([row.valuation_rate for row in rows], [200, 200])
		self.assertEqual([row.balance_value for row in rows], [1000, 2000])

	def test_serial_no_valuation_decides_batch_value(self):
		frappe.db.set_single_value("Stock Settings", "do_not_use_batchwise_valuation", 1)
		for valuation_method, serial_no_wise, expected in (
			("Moving Average", 1, [100, 300]),
			("FIFO", 0, [200, 200]),
		):
			with self.subTest(valuation_method=valuation_method, serial_no_wise=serial_no_wise):
				item = self.make_batch_item(
					valuation_method=valuation_method,
					has_serial_no=1,
					serial_no_series="BWS-.#####",
					use_serial_no_wise_valuation=serial_no_wise,
				)
				for rate in (100, 300):
					make_stock_entry(
						item_code=item, to_warehouse=WH, qty=1, rate=rate, posting_date="2026-06-01"
					)

				self.assertEqual([row.balance_value for row in self.run_report(item)], expected)

	def test_reconciliation_uses_batch_ids(self):
		item = self.make_batch_item()
		make_stock_entry(item_code=item, to_warehouse=WH, qty=10, rate=100, posting_date="2026-06-01")
		(row,) = self.run_report(item)
		batch = frappe.get_doc("Batch", row.batch)
		self.assertNotEqual(batch.name, batch.batch_id)
		self.assertEqual(row.batch_number, batch.batch_id)
		batches = get_itemwise_batch(WH, "2026-06-01", "_Test Company", item)
		self.assertEqual(batches[(item, WH)][0].batch_no, batch.name)
		self.assertEqual(batches[(item, WH)][0].qty, 10)

	def test_opening_qty_from_prior_period(self):
		item = self.make_batch_item()
		make_stock_entry(item_code=item, to_warehouse=WH, qty=8, rate=50, posting_date="2025-12-01")

		(row,) = self.run_report(item)
		self.assertEqual(row.opening_qty, 8)
		self.assertEqual(row.in_qty, 0)
		self.assertEqual(row.balance_qty, 8)

	@ERPNextTestSuite.change_settings(
		"Stock Settings",
		{
			"enable_stock_reservation": 1,
			"auto_reserve_stock": 0,
			"auto_reserve_serial_and_batch": 1,
			"use_serial_batch_fields": 1,
		},
	)
	def test_reserved_stock_after_delivery(self):
		posting_date = today()
		report_dates = {"from_date": posting_date, "to_date": posting_date}
		item = self.make_batch_item()
		make_stock_entry(item_code=item, to_warehouse=WH, qty=10, rate=100, posting_date=posting_date)
		(row,) = self.run_report(item, **report_dates)
		batch = row.batch
		self.assertEqual(row["reserved_stock_(current)"], 0)

		order = make_sales_order(item_code=item, warehouse=WH, qty=6, transaction_date=posting_date)
		order.create_stock_reservation_entries()
		self.assertEqual(self.run_report(item, **report_dates)[0]["reserved_stock_(current)"], 6)

		for delivered_qty, expected_reserved_qty in [(2, 4), (4, 0)]:
			delivery = make_delivery_note(order.name)
			delivery.set_posting_time = 1
			delivery.posting_date = posting_date
			delivery.items[0].qty = delivered_qty
			delivery.items[0].use_serial_batch_fields = 1
			delivery.items[0].batch_no = batch
			delivery.items[0].serial_and_batch_bundle = None
			delivery.insert().submit()
			self.assertEqual(
				self.run_report(item, **report_dates)[0]["reserved_stock_(current)"], expected_reserved_qty
			)
