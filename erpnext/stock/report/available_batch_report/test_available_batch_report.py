# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_days, today

from erpnext.tests.utils import ERPNextTestSuite


class TestAvailableBatchReport(ERPNextTestSuite):
	def test_report_runs_and_lists_batch_qty(self):
		# The report selects Batch columns (expiry_date, and item_name when show_item_name is set)
		# while grouping by SLE columns; the Batch PK must be in the GROUP BY for the report to run
		# on Postgres. show_item_name=1 forces the extra Batch column to be selected.
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.serial_and_batch_bundle.test_serial_and_batch_bundle import (
			get_batch_from_bundle,
		)
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
		from erpnext.stock.report.available_batch_report.available_batch_report import execute

		item = make_item(
			"_Test Available Batch Report Item",
			{"has_batch_no": 1, "create_new_batch": 1, "is_stock_item": 1},
		).name
		se = make_stock_entry(
			item_code=item, target="_Test Warehouse - _TC", qty=7, basic_rate=10, purpose="Material Receipt"
		)
		batch_no = get_batch_from_bundle(se.items[0].serial_and_batch_bundle)

		filters = frappe._dict(to_date=today(), item_code=item, show_item_name=1)
		columns, data = execute(filters)

		self.assertTrue(columns)
		row = next((d for d in data if d.batch_no == batch_no), None)
		self.assertIsNotNone(row)
		self.assertEqual(row.balance_qty, 7)

	def make_batch_with_stock(self, item, expiry_date=None):
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		batch = frappe.get_doc(
			{
				"doctype": "Batch",
				"item": item,
				"batch_id": frappe.generate_hash(length=10),
				"expiry_date": expiry_date,
			}
		).insert()
		make_stock_entry(
			item_code=item,
			target="_Test Warehouse - _TC",
			qty=5,
			basic_rate=10,
			batch_no=batch.name,
			use_serial_batch_fields=1,
			posting_date=add_days(today(), -10),
		)
		return batch.name

	def test_expired_batches_are_left_out_for_a_past_date(self):
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.report.available_batch_report.available_batch_report import execute

		item = make_item(properties={"has_batch_no": 1, "is_stock_item": 1}).name
		self.make_batch_with_stock(item, add_days(today(), -3))
		valid = self.make_batch_with_stock(item, add_days(today(), 30))

		data = execute(frappe._dict(to_date=add_days(today(), -1), item_code=item))[1]

		self.assertEqual([row.batch_no for row in data], [valid])

	def test_batch_issued_after_today_is_listed_for_today(self):
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
		from erpnext.stock.report.available_batch_report.available_batch_report import execute

		item = make_item(properties={"has_batch_no": 1, "is_stock_item": 1}).name
		batch = self.make_batch_with_stock(item)
		make_stock_entry(
			item_code=item,
			source="_Test Warehouse - _TC",
			qty=5,
			batch_no=batch,
			use_serial_batch_fields=1,
			posting_date=add_days(today(), 3),
		)

		data = execute(frappe._dict(to_date=today(), item_code=item))[1]

		self.assertEqual([(row.batch_no, row.balance_qty) for row in data], [(batch, 5)])
