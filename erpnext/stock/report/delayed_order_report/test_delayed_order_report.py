# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.selling.doctype.sales_order.mapper import make_delivery_note
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.delayed_order_report.delayed_order_report import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestDelayedOrderReport(ERPNextTestSuite):
	def run_report(self, **extra):
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"from_date": "2026-06-01",
				"to_date": "2026-06-30",
				"based_on": "Delivery Note",
			}
		)
		filters.update(extra)
		return execute(filters)[1]

	def test_late_order_shows_delay(self):
		item_code = "_Test Item"

		make_stock_entry(
			item_code=item_code,
			target="Stores - _TC",
			qty=10,
			basic_rate=100,
			posting_date="2026-06-01",
		)

		sales_order = make_sales_order(
			item_code=item_code,
			qty=5,
			warehouse="Stores - _TC",
			transaction_date="2026-06-01",
			do_not_submit=True,
		)
		sales_order.delivery_date = "2026-06-05"
		for item in sales_order.items:
			item.delivery_date = "2026-06-05"
		sales_order.submit()

		delivery_note = make_delivery_note(sales_order.name)
		delivery_note.set_posting_time = 1
		delivery_note.posting_date = "2026-06-10"
		delivery_note.insert()
		delivery_note.submit()

		data = self.run_report(sales_order=sales_order.name)

		matching = [row for row in data if row.get("sales_order") == sales_order.name]
		self.assertEqual(len(matching), 1)

		row = matching[0]
		self.assertEqual(frappe.utils.getdate(row.get("delivery_date")), frappe.utils.getdate("2026-06-05"))
		self.assertEqual(frappe.utils.getdate(row.get("posting_date")), frappe.utils.getdate("2026-06-10"))
		self.assertEqual(row.get("delayed_days"), 5)
