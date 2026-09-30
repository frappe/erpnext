# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.accounts.report.delivered_items_to_be_billed.delivered_items_to_be_billed import execute
from erpnext.stock.doctype.delivery_note.mapper import make_sales_invoice
from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.tests.utils import ERPNextTestSuite


class TestDeliveredItemsToBeBilled(ERPNextTestSuite):
	def run_report(self, **extra):
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"posting_date": "2026-06-30",
			}
		)
		filters.update(extra)
		return execute(filters)[1]

	def stock_up_item(self):
		make_stock_entry(
			item_code="_Test Item",
			target="Stores - _TC",
			qty=20,
			basic_rate=100,
			posting_date="2026-05-25",
		)

	def test_unbilled_delivery_note_appears(self):
		self.stock_up_item()
		dn = create_delivery_note(
			item_code="_Test Item",
			warehouse="Stores - _TC",
			qty=5,
			rate=300,
			customer="_Test Customer",
			posting_date="2026-06-01",
		)

		rows = self.run_report(delivery_note=dn.name)
		self.assertEqual(len(rows), 1)

		row = rows[0]
		self.assertEqual(row.name, dn.name)
		self.assertEqual(row.customer, "_Test Customer")
		self.assertEqual(row.item_code, "_Test Item")
		self.assertEqual(row.amount, 1500)
		self.assertEqual(row.billed_amount, 0)
		self.assertEqual(row.returned_amount, 0)
		self.assertEqual(row.pending_amount, 1500)

	def test_fully_billed_delivery_note_drops_out(self):
		self.stock_up_item()
		dn = create_delivery_note(
			item_code="_Test Item",
			warehouse="Stores - _TC",
			qty=5,
			rate=300,
			customer="_Test Customer",
			posting_date="2026-06-01",
		)

		self.assertEqual(len(self.run_report(delivery_note=dn.name)), 1)

		si = make_sales_invoice(dn.name)
		si.posting_date = "2026-06-02"
		si.set_posting_time = 1
		si.insert()
		si.submit()

		self.assertEqual(self.run_report(delivery_note=dn.name), [])

	def test_date_filter_excludes_later_delivery_notes(self):
		self.stock_up_item()
		dn = create_delivery_note(
			item_code="_Test Item",
			warehouse="Stores - _TC",
			qty=5,
			rate=300,
			customer="_Test Customer",
			posting_date="2026-07-15",
		)

		rows = self.run_report(delivery_note=dn.name, posting_date="2026-06-30")
		self.assertEqual(rows, [])
