# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.selling.doctype.sales_order.mapper import make_delivery_note
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.delayed_item_report.delayed_item_report import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestDelayedItemReport(ERPNextTestSuite):
	def run_report(self, **extra):
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"based_on": "Delivery Note",
				"from_date": "2026-06-01",
				"to_date": "2026-06-30",
			}
		)
		filters.update(extra)
		return execute(filters)[1]

	def test_late_delivery_shows_delay(self):
		item = "_Test Item"

		make_stock_entry(
			item_code=item,
			qty=10,
			to_warehouse="Stores - _TC",
			rate=100,
			posting_date="2026-06-01",
			company="_Test Company",
		)

		so = make_sales_order(
			item_code=item,
			qty=10,
			rate=100,
			warehouse="Stores - _TC",
			transaction_date="2026-06-01",
			company="_Test Company",
			do_not_submit=True,
		)
		so.delivery_date = "2026-06-05"
		for row in so.items:
			row.delivery_date = "2026-06-05"
		so.submit()

		dn = make_delivery_note(so.name)
		dn.posting_date = "2026-06-10"
		dn.set_posting_time = 1
		dn.insert()
		dn.submit()

		rows = self.run_report(sales_order=so.name)

		matching = [r for r in rows if r.get("name") == dn.name and r.get("item_code") == item]
		self.assertTrue(matching, f"No report row found for DN {dn.name} / item {item}")

		row = matching[0]
		self.assertEqual(row.get("sales_order"), so.name)
		self.assertEqual(str(row.get("delivery_date")), "2026-06-05")
		self.assertEqual(str(row.get("posting_date")), "2026-06-10")
		# delayed_days = date_diff(actual posting_date, expected delivery_date)
		self.assertEqual(row.get("delayed_days"), 5)

	def make_order_with_deliveries(self, *delivery_dates):
		make_stock_entry(
			item_code="_Test Item",
			qty=10,
			to_warehouse="Stores - _TC",
			rate=100,
			posting_date="2026-06-01",
			company="_Test Company",
		)
		so = make_sales_order(
			item_code="_Test Item",
			qty=5 * len(delivery_dates),
			rate=100,
			warehouse="Stores - _TC",
			transaction_date="2026-06-01",
			company="_Test Company",
			do_not_submit=True,
		)
		so.delivery_date = "2026-06-05"
		for row in so.items:
			row.delivery_date = "2026-06-05"
		so.submit()

		delivery_notes = []
		for posting_date in delivery_dates:
			dn = make_delivery_note(so.name)
			dn.items[0].qty = 5
			dn.posting_date = posting_date
			dn.set_posting_time = 1
			dn.insert()
			dn.submit()
			delivery_notes.append(dn)

		return so, delivery_notes

	def test_returns_are_not_listed_as_deliveries(self):
		from erpnext.stock.doctype.delivery_note.mapper import make_sales_return

		so, delivery_notes = self.make_order_with_deliveries("2026-06-10")
		sales_return = make_sales_return(delivery_notes[0].name)
		sales_return.items[0].qty = -2
		sales_return.posting_date = "2026-06-13"
		sales_return.set_posting_time = 1
		sales_return.insert()
		sales_return.submit()

		rows = self.run_report(sales_order=so.name)

		self.assertEqual([row.name for row in rows], [delivery_notes[0].name])

	def test_group_filters_include_child_groups(self):
		so, delivery_notes = self.make_order_with_deliveries("2026-06-10")

		rows = self.run_report(
			sales_order=so.name, item_group="All Item Groups", customer_group="All Customer Groups"
		)

		self.assertEqual([row.name for row in rows], [delivery_notes[0].name])

	def test_deliveries_on_time_are_not_listed(self):
		so, delivery_notes = self.make_order_with_deliveries("2026-06-03", "2026-06-10")

		rows = self.run_report(sales_order=so.name)

		self.assertEqual([row.name for row in rows], [delivery_notes[1].name])
