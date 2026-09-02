# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.tests.utils import ERPNextTestSuite


class TestStockQtyVsSerialNoCount(ERPNextTestSuite):
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
