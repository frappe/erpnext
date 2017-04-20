# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals

import frappe
from frappe.exceptions import ValidationError
import unittest

from erpnext.stock.doctype.batch.batch import get_batch_qty

class TestBatch(unittest.TestCase):
	def test_item_has_batch_enabled(self):
		self.assertRaises(ValidationError, frappe.get_doc({
			"doctype": "Batch",
			"name": "_test Batch",
			"item": "_Test Item"
		}).save)

	def make_batch_item(self):
		from erpnext.stock.doctype.item.test_item import make_item
		if not frappe.db.exists('ITEM-BATCH-1'):
			make_item('ITEM-BATCH-1', dict(has_batch_no = 1, create_new_batch = 1))

	def test_purchase_receipt(self):
		'''Test automated batch creation from Purchase Receipt'''
		self.make_batch_item()

		receipt = frappe.get_doc(dict(
			doctype = 'Purchase Receipt',
			supplier = '_Test Supplier',
			items = [
				dict(
					item_code = 'ITEM-BATCH-1',
					qty = 100,
					rate = 10
				)
			]
		)).insert()
		receipt.submit()

		self.assertTrue(receipt.items[0].batch_no)
		self.assertEquals(get_batch_qty(receipt.items[0].batch_no, receipt.items[0].warehouse), 100)

		return receipt

	def test_stock_entry(self):
		'''Test batch creation via Stock Entry (Production Order)'''

		self.make_batch_item()

		stock_entry = frappe.get_doc(dict(
			doctype = 'Stock Entry',
			purpose = 'Material Receipt',
			company = '_Test Company',
			items = [
				dict(
					item_code = 'ITEM-BATCH-1',
					qty = 90,
					t_warehouse = '_Test Warehouse - _TC',
					cost_center = 'Main - _TC',
					rate = 10
				)
			]
		)).insert()
		stock_entry.submit()

		self.assertTrue(stock_entry.items[0].batch_no)
		self.assertEquals(get_batch_qty(stock_entry.items[0].batch_no, stock_entry.items[0].t_warehouse), 90)

	def test_batch_split(self):
		'''Test batch splitting'''
		receipt = self.test_purchase_receipt()
		from erpnext.stock.doctype.batch.batch import split_batch

		new_batch = split_batch(receipt.items[0].batch_no, 'ITEM-BATCH-1', receipt.items[0].warehouse, 22)

		self.assertEquals(get_batch_qty(receipt.items[0].batch_no, receipt.items[0].warehouse), 78)
		self.assertEquals(get_batch_qty(new_batch, receipt.items[0].warehouse), 22)


