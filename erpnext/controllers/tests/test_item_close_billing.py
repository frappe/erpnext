# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import flt

from erpnext.controllers.item_close import update_closed_status
from erpnext.controllers.sales_and_purchase_return import make_return_doc
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

	def test_closing_a_row_does_not_inflate_billing_percentage(self):
		receipt = self.make_purchase_receipt()
		self.assertEqual(receipt.per_billed, 0)

		self.close_items(receipt, [receipt.items[1]])

		# nothing was billed, so the receipt must not read as partly billed
		self.assertEqual(receipt.per_billed, 0)
		self.assertEqual(receipt.status, "To Bill")

	def test_closing_every_row_closes_the_receipt(self):
		receipt = self.make_purchase_receipt()

		self.close_items(receipt, receipt.items)

		# nothing was billed, and writing every row off must not claim otherwise
		self.assertEqual(receipt.per_billed, 0)
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
		self.assertEqual(receipt.per_billed, 0)

	def test_unbilled_return_row_can_be_closed(self):
		"""Return rows are closable by design, not by an accident of sign."""
		receipt = self.make_purchase_receipt()
		return_receipt = make_return_doc("Purchase Receipt", receipt.name)
		return_receipt.insert()
		return_receipt.submit()

		row = return_receipt.items[0]
		self.assertLess(row.amount, 0)
		self.assertTrue(return_receipt.is_item_closable(row))

		self.close_items(return_receipt, [row])
		self.assertTrue(return_receipt.items[0].closed)


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

	def test_closing_a_row_does_not_inflate_billing_percentage(self):
		note = self.make_delivery_note()
		self.assertEqual(note.per_billed, 0)

		self.close_items(note, [note.items[1]])

		# nothing was billed, so the note must not read as partially billed
		self.assertEqual(note.per_billed, 0)
		self.assertEqual(note.status, "To Bill")

	def test_closing_every_row_closes_the_note(self):
		note = self.make_delivery_note()

		self.close_items(note, note.items)

		# nothing was billed, and writing every row off must not claim otherwise
		self.assertEqual(note.per_billed, 0)
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

	def test_amending_clears_closed_rows(self):
		"""Frappe keeps no_copy fields when amending, so the flag must be cleared."""
		note = self.make_delivery_note()
		self.close_items(note, [note.items[1]])
		note.cancel()

		amended = frappe.copy_doc(note, ignore_no_copy=True)
		amended.docstatus = 0
		amended.amended_from = note.name
		amended.insert()

		self.assertFalse(any(row.closed for row in amended.items))

	def test_noncanonical_closed_value_is_normalised(self):
		"""A truthy non-1 value must not slip past the exact-match submission guard."""
		note = self.make_delivery_note()

		update_closed_status("Delivery Note", note.name, [note.items[1].name], 2)

		note.reload()
		self.assertEqual(note.items[1].closed, 1)

	def test_unbilled_return_row_can_be_closed(self):
		"""Return rows carry negative amounts and must still be closable."""
		note = self.make_delivery_note()
		return_note = make_return_doc("Delivery Note", note.name)
		return_note.insert()
		return_note.submit()

		row = return_note.items[0]
		self.assertLess(row.amount, 0)
		self.assertTrue(return_note.is_item_closable(row))

		self.close_items(return_note, [row])
		self.assertTrue(return_note.items[0].closed)

	def test_return_row_pending_amount_is_a_magnitude(self):
		"""The dialog shows what is outstanding, so a return row must not read as zero."""
		note = self.make_delivery_note()
		return_note = make_return_doc("Delivery Note", note.name)
		return_note.insert()
		return_note.submit()

		row = return_note.items[0]
		self.assertLess(row.amount, 0)
		pending = abs(flt(row.amount)) - abs(flt(row.billed_amt))
		self.assertEqual(pending, abs(flt(note.items[0].amount)))
		self.assertGreater(pending, 0)

	def test_closing_a_return_row_leaves_the_original_untouched(self):
		"""Writing off a credit note must not disturb what was returned."""
		note = self.make_delivery_note()
		return_note = make_return_doc("Delivery Note", note.name)
		return_note.insert()
		return_note.submit()

		note.reload()
		before = [(row.returned_qty, row.closed) for row in note.items]
		per_returned_before = note.per_returned

		self.close_items(return_note, [return_note.items[0]])

		note.reload()
		self.assertEqual([(row.returned_qty, row.closed) for row in note.items], before)
		self.assertEqual(note.per_returned, per_returned_before)

	def test_closing_the_unbilled_row_completes_the_note(self):
		"""The point of the feature: a written off row stops holding billing open."""
		note = self.make_delivery_note()
		invoice = make_sales_invoice(note.name)
		invoice.items = [item for item in invoice.items if item.item_code == self.first_item]
		invoice.insert()
		invoice.submit()

		note.reload()
		self.assertEqual(note.per_billed, 50)

		self.close_items(note, [note.items[1]])

		self.assertEqual(note.per_billed, 100)
		self.assertEqual(note.status, "Completed")

