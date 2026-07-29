# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from erpnext.controllers.item_close import update_closed_status
from erpnext.stock.doctype.delivery_note.mapper import make_sales_invoice
from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.purchase_receipt.mapper import make_purchase_invoice
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.tests.utils import ERPNextTestSuite

WAREHOUSE = "_Test Warehouse - _TC"


class TestPurchaseReceiptItemClose(ERPNextTestSuite):
	def setUp(self):
		self.first_item = make_item(properties={"is_stock_item": 1}).name
		self.second_item = make_item(properties={"is_stock_item": 1}).name

	def make_purchase_receipt(self):
		receipt = make_purchase_receipt(
			item_code=self.first_item, qty=10, rate=100, warehouse=WAREHOUSE, do_not_submit=True
		)
		receipt.append(
			"items",
			{
				"item_code": self.second_item,
				"warehouse": WAREHOUSE,
				"qty": 10,
				"rate": 100,
			},
		)
		receipt.save()
		receipt.submit()
		return receipt

	def close_items(self, doc, rows, closed=1):
		update_closed_status(doc.doctype, doc.name, [row.name for row in rows], closed)
		doc.reload()

	def test_closing_row_settles_billing_percentage(self):
		receipt = self.make_purchase_receipt()
		self.assertEqual(receipt.per_billed, 0)

		self.close_items(receipt, [receipt.items[1]])

		self.assertEqual(receipt.per_billed, 50)

	def test_closing_every_row_closes_the_receipt(self):
		receipt = self.make_purchase_receipt()

		self.close_items(receipt, receipt.items)

		self.assertEqual(receipt.per_billed, 100)
		self.assertEqual(receipt.status, "Closed")

	def test_closed_row_is_not_mapped_to_purchase_invoice(self):
		receipt = self.make_purchase_receipt()
		self.close_items(receipt, [receipt.items[1]])

		invoice = make_purchase_invoice(receipt.name)

		self.assertEqual([item.item_code for item in invoice.items], [self.first_item])

	def test_billing_a_closed_row_is_blocked(self):
		receipt = self.make_purchase_receipt()
		invoice = make_purchase_invoice(receipt.name)

		self.close_items(receipt, [receipt.items[1]])

		invoice.insert()
		self.assertRaises(frappe.ValidationError, invoice.submit)

	def test_parent_reopen_is_blocked_when_all_rows_are_closed(self):
		receipt = self.make_purchase_receipt()
		self.close_items(receipt, receipt.items)

		self.assertRaises(frappe.ValidationError, receipt.update_status, "Submitted")

	def test_reopening_one_row_reopens_the_receipt(self):
		receipt = self.make_purchase_receipt()
		self.close_items(receipt, receipt.items)

		self.close_items(receipt, [receipt.items[1]], closed=0)

		self.assertNotEqual(receipt.status, "Closed")
		self.assertEqual(receipt.per_billed, 50)


class TestDeliveryNoteItemClose(ERPNextTestSuite):
	def setUp(self):
		self.first_item = make_item(properties={"is_stock_item": 1}).name
		self.second_item = make_item(properties={"is_stock_item": 1}).name
		for item_code in (self.first_item, self.second_item):
			make_stock_entry(item_code=item_code, target=WAREHOUSE, qty=100, basic_rate=50)

	def make_delivery_note(self):
		note = create_delivery_note(
			item_code=self.first_item, qty=10, rate=100, warehouse=WAREHOUSE, do_not_save=True
		)
		note.append(
			"items",
			{
				"item_code": self.second_item,
				"warehouse": WAREHOUSE,
				"qty": 10,
				"rate": 100,
			},
		)
		note.insert()
		note.submit()
		return note

	def close_items(self, doc, rows, closed=1):
		update_closed_status(doc.doctype, doc.name, [row.name for row in rows], closed)
		doc.reload()

	def test_closing_row_settles_billing_percentage(self):
		note = self.make_delivery_note()
		self.assertEqual(note.per_billed, 0)

		self.close_items(note, [note.items[1]])

		self.assertEqual(note.per_billed, 50)

	def test_closing_every_row_closes_the_note(self):
		note = self.make_delivery_note()

		self.close_items(note, note.items)

		self.assertEqual(note.per_billed, 100)
		self.assertEqual(note.status, "Closed")

	def test_closed_row_is_not_mapped_to_sales_invoice(self):
		note = self.make_delivery_note()
		self.close_items(note, [note.items[1]])

		invoice = make_sales_invoice(note.name)

		self.assertEqual([item.item_code for item in invoice.items], [self.first_item])

	def test_billing_a_closed_row_is_blocked(self):
		note = self.make_delivery_note()
		invoice = make_sales_invoice(note.name)

		self.close_items(note, [note.items[1]])

		invoice.insert()
		self.assertRaises(frappe.ValidationError, invoice.submit)

	def test_closing_a_row_does_not_mark_it_returned(self):
		note = self.make_delivery_note()

		self.close_items(note, note.items)

		self.assertEqual(note.per_returned, 0)
		self.assertEqual(note.status, "Closed")
