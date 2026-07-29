# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import add_days, flt, nowdate

from erpnext.buying.doctype.purchase_order.mapper import (
	get_mapped_purchase_invoice,
	make_purchase_receipt,
)
from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.controllers.item_close import update_closed_status
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.tests.utils import ERPNextTestSuite

WAREHOUSE = "_Test Warehouse - _TC"


def get_ordered_qty(item_code):
	return flt(frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": WAREHOUSE}, "ordered_qty"))


class TestPurchaseOrderItemClose(ERPNextTestSuite):
	def setUp(self):
		self.first_item = make_item(properties={"is_stock_item": 1}).name
		self.second_item = make_item(properties={"is_stock_item": 1}).name

	def make_purchase_order(self):
		po = create_purchase_order(item_code=self.first_item, qty=10, rate=100, do_not_save=True)
		po.append(
			"items",
			{
				"item_code": self.second_item,
				"warehouse": WAREHOUSE,
				"qty": 10,
				"rate": 100,
				"schedule_date": add_days(nowdate(), 1),
			},
		)
		po.set_missing_values()
		po.insert()
		po.submit()
		return po

	def close_items(self, po, rows, closed=1):
		update_closed_status("Purchase Order", po.name, [row.name for row in rows], closed)
		po.reload()

	def test_closing_row_releases_ordered_qty(self):
		po = self.make_purchase_order()
		self.assertEqual(get_ordered_qty(self.second_item), 10)

		self.close_items(po, [po.items[1]])

		self.assertEqual(get_ordered_qty(self.second_item), 0)
		self.assertEqual(get_ordered_qty(self.first_item), 10)

	def test_closing_row_settles_receiving_percentage(self):
		po = self.make_purchase_order()

		receipt = make_purchase_receipt(po.name)
		receipt.items = [item for item in receipt.items if item.item_code == self.first_item]
		receipt.insert()
		receipt.submit()

		po.reload()
		self.assertEqual(po.per_received, 50)
		self.assertEqual(po.status, "To Receive and Bill")

		self.close_items(po, [po.items[1]])

		self.assertEqual(po.per_received, 100)
		self.assertEqual(po.status, "To Bill")

	def test_closing_every_row_closes_the_order(self):
		po = self.make_purchase_order()

		self.close_items(po, po.items)

		self.assertEqual(po.status, "Closed")
		self.assertEqual(get_ordered_qty(self.first_item), 0)
		self.assertEqual(get_ordered_qty(self.second_item), 0)

	def test_parent_reopen_is_blocked_when_all_rows_are_closed(self):
		po = self.make_purchase_order()
		self.close_items(po, po.items)

		self.assertRaises(frappe.ValidationError, po.update_status, "Submitted")

		po.reload()
		self.assertEqual(po.status, "Closed")
		self.assertTrue(all(row.closed for row in po.items))

	def test_reopening_all_rows_restores_the_order(self):
		po = self.make_purchase_order()
		self.close_items(po, po.items)
		self.assertEqual(po.status, "Closed")

		self.close_items(po, po.items, closed=0)

		self.assertFalse(any(row.closed for row in po.items))
		self.assertEqual(po.per_received, 0)
		self.assertEqual(po.status, "To Receive and Bill")
		self.assertEqual(get_ordered_qty(self.first_item), 10)

	def test_reopening_one_row_reopens_the_parent(self):
		po = self.make_purchase_order()
		self.close_items(po, po.items)

		self.close_items(po, [po.items[1]], closed=0)

		self.assertEqual(po.status, "To Receive and Bill")
		self.assertTrue(po.items[0].closed)
		self.assertFalse(po.items[1].closed)
		# nothing received, and the closed row is written off rather than counted
		self.assertEqual(po.per_received, 0)
		self.assertEqual(get_ordered_qty(self.second_item), 10)
		self.assertEqual(get_ordered_qty(self.first_item), 0)

	def test_settled_row_cannot_be_closed(self):
		po = self.make_purchase_order()

		receipt = make_purchase_receipt(po.name)
		receipt.insert()
		receipt.submit()
		invoice = get_mapped_purchase_invoice(po.name)
		invoice.insert()
		invoice.submit()

		po.reload()
		self.assertEqual(po.status, "Completed")
		self.assertRaises(frappe.ValidationError, self.close_items, po, [po.items[0]])

	def test_received_but_unbilled_row_can_be_closed(self):
		po = self.make_purchase_order()

		receipt = make_purchase_receipt(po.name)
		receipt.insert()
		receipt.submit()

		po.reload()
		self.assertEqual(po.status, "To Bill")

		self.close_items(po, po.items)

		self.assertEqual(po.per_billed, 100)
		self.assertEqual(po.status, "Closed")

	def test_receipt_is_not_offered_when_the_rest_is_closed(self):
		po = self.make_purchase_order()

		receipt = make_purchase_receipt(po.name)
		receipt.items = [item for item in receipt.items if item.item_code == self.first_item]
		receipt.insert()
		receipt.submit()

		po.reload()
		self.close_items(po, [po.items[1]])

		self.assertEqual(po.status, "To Bill")
		self.assertFalse(po.has_pending_receivable_qty())
		self.assertFalse(make_purchase_receipt(po.name).get("items"))

	def test_reopening_partly_closed_order_keeps_row_flags(self):
		po = self.make_purchase_order()
		self.close_items(po, [po.items[1]])

		po.update_status("Closed")
		po.reload()
		self.assertEqual(po.status, "Closed")

		po.update_status("Submitted")
		po.reload()

		self.assertFalse(po.items[0].closed)
		self.assertTrue(po.items[1].closed)
		self.assertEqual(get_ordered_qty(self.first_item), 10)
		self.assertEqual(get_ordered_qty(self.second_item), 0)

	def test_closed_row_is_not_mapped_to_purchase_receipt(self):
		po = self.make_purchase_order()
		self.close_items(po, [po.items[1]])

		receipt = make_purchase_receipt(po.name)

		self.assertEqual([item.item_code for item in receipt.items], [self.first_item])

	def test_receiving_a_closed_row_is_blocked(self):
		po = self.make_purchase_order()
		receipt = make_purchase_receipt(po.name)

		self.close_items(po, [po.items[1]])

		receipt.insert()
		self.assertRaises(frappe.ValidationError, receipt.submit)

	def test_reopening_a_row_restores_pending_qty(self):
		po = self.make_purchase_order()
		self.close_items(po, [po.items[1]])
		self.assertEqual(get_ordered_qty(self.second_item), 0)

		self.close_items(po, [po.items[1]], closed=0)

		self.assertEqual(get_ordered_qty(self.second_item), 10)
		self.assertEqual(po.per_received, 0)
		self.assertEqual(po.status, "To Receive and Bill")

	def test_closing_is_rejected_for_unsupported_doctype(self):
		self.assertRaises(
			frappe.ValidationError,
			update_closed_status,
			"Material Request",
			"any-name",
			["any-row"],
			1,
		)

	def test_amending_clears_closed_rows(self):
		"""Frappe keeps no_copy fields when amending, so the flag must be cleared."""
		po = self.make_purchase_order()
		self.close_items(po, [po.items[1]])
		po.cancel()

		amended = frappe.copy_doc(po, ignore_no_copy=True)
		amended.docstatus = 0
		amended.amended_from = po.name
		amended.insert()

		self.assertFalse(any(row.closed for row in amended.items))
