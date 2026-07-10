# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.serial_no_and_batch_traceability.serial_no_and_batch_traceability import (
	execute,
)
from erpnext.tests.utils import ERPNextTestSuite

SERIAL_ITEM = "_Test Serialized Item With Series"


class TestSerialNoAndBatchTraceability(ERPNextTestSuite):
	def run_report(self, **extra):
		filters = frappe._dict({"company": "_Test Company"})
		filters.update(extra)
		return execute(filters)[1]

	def get_received_serial_no(self, receipt):
		bundle = frappe.db.get_value(
			"Stock Entry Detail",
			{"parent": receipt.name, "item_code": SERIAL_ITEM},
			"serial_and_batch_bundle",
		)
		return frappe.db.get_value("Serial and Batch Entry", {"parent": bundle}, "serial_no")

	def test_serial_movements_traced(self):
		"""Backward trace should surface the receipt voucher the serial came in through."""
		receipt = make_stock_entry(
			item_code=SERIAL_ITEM,
			to_warehouse="Stores - _TC",
			qty=2,
			rate=100,
			posting_date="2026-06-01",
			company="_Test Company",
		)
		serial_no = self.get_received_serial_no(receipt)

		rows = self.run_report(
			item_code=SERIAL_ITEM,
			serial_nos=[serial_no],
			traceability_direction="Backward",
		)

		traced = {row["reference_name"]: row for row in rows if row.get("reference_name")}
		self.assertIn(receipt.name, traced)

		receipt_row = traced[receipt.name]
		self.assertEqual(receipt_row["serial_no"], serial_no)
		self.assertEqual(receipt_row["item_code"], SERIAL_ITEM)
		self.assertEqual(receipt_row["reference_doctype"], "Stock Entry")
		self.assertEqual(receipt_row["warehouse"], "Stores - _TC")
		self.assertEqual(receipt_row["direction"], "Backward")
		self.assertGreater(receipt_row["qty"], 0)

	def test_forward_and_backward_directions(self):
		"""'Both' should trace backward to the receipt and forward to the outward delivery."""
		receipt = make_stock_entry(
			item_code=SERIAL_ITEM,
			to_warehouse="Stores - _TC",
			qty=2,
			rate=100,
			posting_date="2026-06-01",
			company="_Test Company",
		)
		serial_no = self.get_received_serial_no(receipt)

		delivery_note = create_delivery_note(
			item_code=SERIAL_ITEM,
			qty=1,
			serial_no=[serial_no],
			warehouse="Stores - _TC",
			customer="_Test Customer",
			posting_date="2026-06-03",
			company="_Test Company",
		)

		rows = self.run_report(
			item_code=SERIAL_ITEM,
			serial_nos=[serial_no],
			traceability_direction="Both",
		)

		traced = {row["reference_name"]: row for row in rows if row.get("reference_name")}

		self.assertIn(receipt.name, traced)
		self.assertEqual(traced[receipt.name]["direction"], "Backward")

		self.assertIn(delivery_note.name, traced)
		forward_row = traced[delivery_note.name]
		self.assertEqual(forward_row["reference_doctype"], "Delivery Note")
		self.assertEqual(forward_row["serial_no"], serial_no)
		self.assertEqual(forward_row["direction"], "Forward")
		self.assertEqual(forward_row["customer"], delivery_note.customer)
		self.assertLess(forward_row["qty"], 0)
