# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.stock_qty_vs_serial_no_count.stock_qty_vs_serial_no_count import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestStockQtyVsSerialNoCount(ERPNextTestSuite):
	def run_report(self, **extra):
		filters = {
			"company": "_Test Company",
			"warehouse": "Stores - _TC",
		}
		filters.update(extra)
		return execute(frappe._dict(filters))[1]

	def test_serial_count_matches_stock_qty(self):
		item = "_Test Serialized Item With Series"
		make_stock_entry(
			item_code=item,
			to_warehouse="Stores - _TC",
			qty=3,
			rate=100,
			posting_date="2026-06-01",
		)

		data = self.run_report()
		row = next((entry for entry in data if entry["item_code"] == item), None)

		self.assertIsNotNone(row, "Serialized item should be present in the report")
		# Serial No count should equal the stock qty in this warehouse, regardless of
		# how many serials the shared master has accumulated across tests.
		self.assertEqual(row["total"], row["stock_qty"])
		self.assertEqual(row["difference"], 0)

	def test_warehouse_is_validated(self):
		with self.assertRaises(frappe.ValidationError):
			execute(
				frappe._dict(
					{
						"company": "_Test Company",
						"warehouse": "Non Existent Warehouse - XYZ",
					}
				)
			)

	def test_sync_serial_no_status(self):
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
		from erpnext.stock.report.stock_qty_vs_serial_no_count.stock_qty_vs_serial_no_count import (
			sync_serial_no_status_for_warehouse,
		)

		item = "_Test Serialized Item With Series"
		warehouse = "Stores - _TC"
		se = make_stock_entry(item_code=item, to_warehouse=warehouse, qty=2, rate=100)
		serial_no = frappe.get_all(
			"Serial and Batch Entry",
			{"parent": se.items[0].serial_and_batch_bundle},
			pluck="serial_no",
		)[0]

		create_delivery_note(
			item_code=item,
			warehouse=warehouse,
			qty=1,
			serial_no=serial_no,
			use_serial_batch_fields=1,
		)
		self.assertEqual(frappe.db.get_value("Serial No", serial_no, "status"), "Delivered")

		frappe.db.set_value("Serial No", serial_no, {"status": "Active", "warehouse": warehouse})

		sync_serial_no_status_for_warehouse(warehouse, item_code=item)

		details = frappe.db.get_value("Serial No", serial_no, ["status", "warehouse"], as_dict=True)
		self.assertEqual(details.status, "Delivered")
		self.assertFalse(details.warehouse)
