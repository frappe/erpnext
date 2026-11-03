# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.batch_wise_balance_history.batch_wise_balance_history import execute

WH = "Stores - _TC"
VALUATION_RATE = 9
BALANCE_VALUE = 10


class TestBatchWiseBalanceHistory(FrappeTestCase):
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
		self.assertEqual([row[VALUATION_RATE] for row in rows], [200, 200])
		self.assertEqual([row[BALANCE_VALUE] for row in rows], [1000, 2000])

	def test_serial_no_batches_keep_serial_wise_value(self):
		frappe.db.set_single_value("Stock Settings", "do_not_use_batchwise_valuation", 1)
		item = self.make_batch_item(
			valuation_method="Moving Average",
			has_serial_no=1,
			serial_no_series="BWS-.#####",
		)
		for rate in (100, 300):
			make_stock_entry(item_code=item, to_warehouse=WH, qty=1, rate=rate, posting_date="2026-06-01")

		self.assertEqual([row[BALANCE_VALUE] for row in self.run_report(item)], [100, 300])
