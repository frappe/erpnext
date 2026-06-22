# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import today

from erpnext.tests.utils import ERPNextTestSuite


class TestAvailableBatchReport(ERPNextTestSuite):
	@staticmethod
	def _cancel_and_delete_stock_entry(name):
		if not frappe.db.exists("Stock Entry", name):
			return
		doc = frappe.get_doc("Stock Entry", name)
		if doc.docstatus == 1:
			doc.cancel()
		frappe.delete_doc("Stock Entry", name, force=1)

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
		# make_item is idempotent (returns the existing item), but each receipt stacks a new batch,
		# so cancel+delete the stock entry to keep repeated runs clean.
		self.addCleanup(self._cancel_and_delete_stock_entry, se.name)
		batch_no = get_batch_from_bundle(se.items[0].serial_and_batch_bundle)

		filters = frappe._dict(to_date=today(), item_code=item, show_item_name=1)
		columns, data = execute(filters)

		self.assertTrue(columns)
		row = next((d for d in data if d.batch_no == batch_no), None)
		self.assertIsNotNone(row)
		self.assertEqual(row.balance_qty, 7)
