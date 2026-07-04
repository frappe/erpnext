# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.serial_no_ledger.serial_no_ledger import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestSerialNoLedger(ERPNextTestSuite):
	def run_report(self, **extra):
		filters = {
			"company": "_Test Company",
			"warehouse": "Stores - _TC",
			"posting_date": "2026-06-30",
		}
		filters.update(extra)
		return execute(frappe._dict(filters))[1]

	def make_serial_item(self) -> str:
		return "_Test Serialized Item With Series"

	def test_receipt_appears_in_serial_ledger(self):
		item = self.make_serial_item()
		stock_entry = make_stock_entry(
			item_code=item,
			to_warehouse="Stores - _TC",
			qty=2,
			rate=100,
			posting_date="2026-06-01",
		)

		serial_nos = frappe.get_all("Serial No", {"item_code": item}, pluck="name")
		self.assertEqual(len(serial_nos), 2)
		serial_no = serial_nos[0]

		data = self.run_report(item_code=item, serial_no=serial_no)

		self.assertEqual(len(data), 1)
		row = data[0]
		self.assertEqual(row["serial_no"], serial_no)
		self.assertEqual(row["voucher_type"], "Stock Entry")
		self.assertEqual(row["voucher_no"], stock_entry.name)
		self.assertEqual(row["warehouse"], "Stores - _TC")
		self.assertEqual(row["qty"], 1)
		self.assertEqual(row["valuation_rate"], 100)

	def test_filter_by_item_lists_all_received_serials(self):
		item = self.make_serial_item()
		make_stock_entry(
			item_code=item,
			to_warehouse="Stores - _TC",
			qty=2,
			rate=150,
			posting_date="2026-06-01",
		)

		serial_nos = frappe.get_all("Serial No", {"item_code": item}, pluck="name")

		data = self.run_report(item_code=item)

		ledger_serials = sorted(row["serial_no"] for row in data)
		self.assertEqual(ledger_serials, sorted(serial_nos))
		for row in data:
			self.assertEqual(row["qty"], 1)
			self.assertEqual(row["valuation_rate"], 150)
