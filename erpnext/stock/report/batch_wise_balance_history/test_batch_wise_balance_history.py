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

	def test_non_batchwise_valuation_at_report_cutoff(self):
		frappe.db.set_single_value("Stock Settings", "do_not_use_batchwise_valuation", 0)
		item = self.make_batch_item(valuation_method="Moving Average")
		for date, rate in [("2026-06-01", 100), ("2026-06-02", 300)]:
			make_stock_entry(
				item_code=item,
				to_warehouse=WH,
				qty=10,
				rate=rate,
				posting_date=date,
				posting_time="09:00:00",
			)

		# Enabling pooled valuation must also include batches created with batch-wise valuation.
		self.assertEqual(
			frappe.get_all("Batch", filters={"item": item}, pluck="use_batchwise_valuation"), [1, 1]
		)
		frappe.db.set_single_value("Stock Settings", "do_not_use_batchwise_valuation", 1)
		rows = self.run_report(item, to_date="2026-06-02")
		self.assertEqual(len(rows), 2)
		self.assertEqual([row.valuation_rate for row in rows], [200, 200])
		self.assertEqual([row.balance_value for row in rows], [2000, 2000])
		(first_row,) = self.run_report(item, to_date="2026-06-01")
		first_batch = first_row.batch
		make_stock_entry(
			item_code=item,
			from_warehouse=WH,
			qty=5,
			batch_no=first_batch,
			posting_date="2026-06-03",
			posting_time="09:00:00",
		)
		make_stock_entry(
			item_code=item,
			to_warehouse=WH,
			qty=5,
			rate=600,
			posting_date="2026-06-03",
			posting_time="12:00:00",
		)

		for to_date, cutoff, expected_rate, expected_qty in [
			("2026-06-02", None, 200, 10),
			("2026-06-03", "2026-06-03 10:00:00", 200, 5),
			("2026-06-03", None, 300, 5),
		]:
			with self.subTest(to_date=to_date, cutoff=cutoff):
				filters = frappe._dict(
					company="_Test Company",
					item_code=item,
					warehouse=WH,
					batch_no=first_batch,
					from_date="2026-06-01",
					to_date=to_date,
					to_datetime=cutoff,
				)
				(row,) = execute(filters)[1]
				self.assertEqual(row.balance_qty, expected_qty)
				self.assertEqual(row.valuation_rate, expected_rate)
				self.assertEqual(row.balance_value, expected_qty * expected_rate)

		make_stock_entry(
			item_code=item,
			from_warehouse=WH,
			qty=5,
			batch_no=first_batch,
			posting_date="2026-06-04",
			posting_time="09:00:00",
		)
		filters.to_date = "2026-06-04"
		(row,) = execute(filters)[1]
		self.assertEqual(row.balance_qty, 0)
		self.assertEqual(row.valuation_rate, 0)
		self.assertEqual(row.balance_value, 0)

	def test_batchwise_valuation_keeps_batch_cost(self):
		for method in ("Moving Average", "FIFO"):
			with self.subTest(valuation_method=method):
				frappe.db.set_single_value(
					"Stock Settings", "do_not_use_batchwise_valuation", method == "FIFO"
				)
				item = self.make_batch_item(valuation_method=method)
				for date, rate in [("2026-06-01", 100), ("2026-06-02", 300)]:
					make_stock_entry(item_code=item, to_warehouse=WH, qty=10, rate=rate, posting_date=date)
				(first_row,) = self.run_report(item, to_date="2026-06-01")
				if method == "Moving Average":
					# Represent a legacy batch alongside a newer batch valued batch-wise.
					frappe.db.set_value("Batch", first_row.batch, "use_batchwise_valuation", 0)
				make_stock_entry(
					item_code=item,
					from_warehouse=WH,
					batch_no=first_row.batch,
					qty=5,
					posting_date="2026-06-03",
				)
				rows = self.run_report(item)
				self.assertEqual(sorted(row.valuation_rate for row in rows), [100, 300])
				self.assertEqual(sorted(row.balance_value for row in rows), [500, 3000])

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
