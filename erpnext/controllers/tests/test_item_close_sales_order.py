# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import add_days, flt, nowdate

from erpnext.controllers.item_close import update_closed_status
from erpnext.selling.doctype.sales_order.mapper import make_delivery_note, make_sales_invoice
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.tests.utils import ERPNextTestSuite

WAREHOUSE = "_Test Warehouse - _TC"


def get_reserved_qty(item_code):
	return flt(
		frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": WAREHOUSE}, "reserved_qty")
	)


class TestSalesOrderItemClose(ERPNextTestSuite):
	def setUp(self):
		self.first_item = make_item(properties={"is_stock_item": 1}).name
		self.second_item = make_item(properties={"is_stock_item": 1}).name
		for item_code in (self.first_item, self.second_item):
			make_stock_entry(item_code=item_code, target=WAREHOUSE, qty=100, basic_rate=50)

	def make_sales_order(self):
		so = make_sales_order(
			item_code=self.first_item, qty=10, rate=100, warehouse=WAREHOUSE, do_not_submit=True
		)
		so.append(
			"items",
			{
				"item_code": self.second_item,
				"warehouse": WAREHOUSE,
				"qty": 10,
				"rate": 100,
				"delivery_date": add_days(nowdate(), 1),
			},
		)
		so.save()
		so.submit()
		return so

	def close_items(self, so, rows, closed=1):
		update_closed_status("Sales Order", so.name, [row.name for row in rows], closed)
		so.reload()

	def test_closing_row_releases_reserved_qty(self):
		so = self.make_sales_order()
		self.assertEqual(get_reserved_qty(self.second_item), 10)

		self.close_items(so, [so.items[1]])

		self.assertEqual(get_reserved_qty(self.second_item), 0)
		self.assertEqual(get_reserved_qty(self.first_item), 10)

	def test_closing_row_settles_delivery_percentage(self):
		so = self.make_sales_order()

		note = make_delivery_note(so.name)
		note.items = [item for item in note.items if item.item_code == self.first_item]
		note.insert()
		note.submit()

		so.reload()
		self.assertEqual(so.per_delivered, 50)

		self.close_items(so, [so.items[1]])

		self.assertEqual(so.per_delivered, 100)
		self.assertEqual(so.delivery_status, "Fully Delivered")

	def test_closing_every_row_closes_the_order(self):
		so = self.make_sales_order()

		self.close_items(so, so.items)

		self.assertEqual(so.status, "Closed")
		self.assertEqual(get_reserved_qty(self.first_item), 0)
		self.assertEqual(get_reserved_qty(self.second_item), 0)

	def test_reopening_one_row_reopens_the_parent(self):
		so = self.make_sales_order()
		self.close_items(so, so.items)

		self.close_items(so, [so.items[1]], closed=0)

		self.assertNotEqual(so.status, "Closed")
		self.assertTrue(so.items[0].closed)
		self.assertFalse(so.items[1].closed)
		self.assertEqual(get_reserved_qty(self.second_item), 10)
		self.assertEqual(get_reserved_qty(self.first_item), 0)

	def test_parent_reopen_is_blocked_when_all_rows_are_closed(self):
		so = self.make_sales_order()
		self.close_items(so, so.items)

		self.assertRaises(frappe.ValidationError, so.update_status, "Draft")

		so.reload()
		self.assertEqual(so.status, "Closed")

	def test_closed_row_is_not_mapped_to_delivery_note(self):
		so = self.make_sales_order()
		self.close_items(so, [so.items[1]])

		note = make_delivery_note(so.name)

		self.assertEqual([item.item_code for item in note.items], [self.first_item])

	def test_closed_row_is_not_mapped_to_sales_invoice(self):
		so = self.make_sales_order()
		self.close_items(so, [so.items[1]])

		invoice = make_sales_invoice(so.name)

		self.assertEqual([item.item_code for item in invoice.items], [self.first_item])

	def test_delivering_a_closed_row_is_blocked(self):
		so = self.make_sales_order()
		note = make_delivery_note(so.name)

		self.close_items(so, [so.items[1]])

		note.insert()
		self.assertRaises(frappe.ValidationError, note.submit)

	def test_settled_row_cannot_be_closed(self):
		so = self.make_sales_order()

		note = make_delivery_note(so.name)
		note.insert()
		note.submit()
		invoice = make_sales_invoice(so.name)
		invoice.insert()
		invoice.submit()

		so.reload()
		self.assertRaises(frappe.ValidationError, self.close_items, so, [so.items[0]])
