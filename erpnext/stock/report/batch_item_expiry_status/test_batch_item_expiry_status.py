# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.batch_item_expiry_status.batch_item_expiry_status import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestBatchItemExpiryStatus(ERPNextTestSuite):
	def run_report(self, **extra):
		filters = frappe._dict(
			{
				"from_date": "2026-01-01",
				"to_date": "2026-12-31",
				"company": "_Test Company",
			}
		)
		filters.update(extra)
		return execute(filters)[1]

	def test_batch_listed_with_balance(self):
		item = make_item(
			properties={
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "BIE-.#####",
				"has_expiry_date": 1,
				"shelf_life_in_days": 30,
			}
		).name

		make_stock_entry(
			item_code=item,
			to_warehouse="_Test Warehouse - _TC",
			qty=10,
			rate=100,
			posting_date="2026-06-01",
		)

		batch_no = frappe.db.get_value("Batch", {"item": item}, "name")
		self.assertTrue(batch_no, "Stock entry did not auto-create a batch")

		data = self.run_report(item=item)

		# Columns: [item, item_name, batch, stock_uom, quantity, expires_on, expiry_in_days]
		row = next((r for r in data if r[2] == batch_no), None)
		self.assertIsNotNone(row, f"Batch {batch_no} not found in report for item {item}")

		self.assertEqual(row[0], item)
		self.assertEqual(row[2], batch_no)
		self.assertEqual(row[4], 10)
		# expiry = batch manufacturing_date + 30 day shelf life; matches the Batch record
		batch_expiry = frappe.db.get_value("Batch", batch_no, "expiry_date")
		self.assertIsNotNone(row[5], "Expiry date should be set for a batch with shelf life")
		self.assertEqual(frappe.utils.getdate(row[5]), frappe.utils.getdate(batch_expiry))
		# Expiry (In Days) column = days until expiry
		expected_days = max((frappe.utils.getdate(batch_expiry) - frappe.utils.datetime.date.today()).days, 0)
		self.assertEqual(row[6], expected_days)
