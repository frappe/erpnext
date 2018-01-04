# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals

import frappe
from frappe.exceptions import ValidationError
import unittest

from erpnext.stock.doctype.batch.batch import get_batch_qty, UnableToSelectBatchError, get_batch_no

class TestBatch(unittest.TestCase):

	def test_item_has_batch_enabled(self):
		self.assertRaises(ValidationError, frappe.get_doc({
			"doctype": "Batch",
			"name": "_test Batch",
			"item": "_Test Item"
		}).save)

	@classmethod
	def make_batch_item(cls, item_name):
		from erpnext.stock.doctype.item.test_item import make_item
		if not frappe.db.exists(item_name):
			make_item(item_name, dict(has_batch_no = 1, create_new_batch = 1))

	def test_purchase_receipt(self, batch_qty = 100):
		'''Test automated batch creation from Purchase Receipt'''
		self.make_batch_item('ITEM-BATCH-1')

		receipt = frappe.get_doc(dict(
			doctype='Purchase Receipt',
			supplier='_Test Supplier',
			items=[
				dict(
					item_code='ITEM-BATCH-1',
					qty=batch_qty,
					rate=10
				)
			]
		)).insert()
		receipt.submit()

		self.assertTrue(receipt.items[0].batch_no)
		self.assertEquals(get_batch_qty(receipt.items[0].batch_no,
			receipt.items[0].warehouse), batch_qty)

		return receipt

	def test_stock_entry_incoming(self):
		'''Test batch creation via Stock Entry (Production Order)'''

		self.make_batch_item('ITEM-BATCH-1')

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

	def test_delivery_note(self):
		'''Test automatic batch selection for outgoing items'''
		batch_qty = 15
		receipt = self.test_purchase_receipt(batch_qty)
		item_code = 'ITEM-BATCH-1'

		delivery_note = frappe.get_doc(dict(
			doctype='Delivery Note',
			customer='_Test Customer',
			company=receipt.company,
			items=[
				dict(
					item_code=item_code,
					qty=batch_qty,
					rate=10,
					warehouse=receipt.items[0].warehouse
				)
			]
		)).insert()
		delivery_note.submit()

		# shipped from FEFO batch
		self.assertEquals(
			delivery_note.items[0].batch_no,
			get_batch_no(item_code, receipt.items[0].warehouse, batch_qty)
		)

	def test_delivery_note_fail(self):
		'''Test automatic batch selection for outgoing items'''
		receipt = self.test_purchase_receipt(100)
		delivery_note = frappe.get_doc(dict(
			doctype = 'Delivery Note',
			customer = '_Test Customer',
			company = receipt.company,
			items = [
				dict(
					item_code = 'ITEM-BATCH-1',
					qty = 5000,
					rate = 10,
					warehouse = receipt.items[0].warehouse
				)
			]
		))
		self.assertRaises(UnableToSelectBatchError, delivery_note.insert)

	def test_stock_entry_outgoing(self):
		'''Test automatic batch selection for outgoing stock entry'''

		batch_qty = 16
		receipt = self.test_purchase_receipt(batch_qty)
		item_code = 'ITEM-BATCH-1'

		stock_entry = frappe.get_doc(dict(
			doctype='Stock Entry',
			purpose='Material Issue',
			company=receipt.company,
			items=[
				dict(
					item_code=item_code,
					qty=batch_qty,
					s_warehouse=receipt.items[0].warehouse,
				)
			]
		)).insert()
		stock_entry.submit()

		# assert same batch is selected
		self.assertEqual(
			stock_entry.items[0].batch_no,
			get_batch_no(item_code, receipt.items[0].warehouse, batch_qty)
		)

	def test_batch_split(self):
		'''Test batch splitting'''
		receipt = self.test_purchase_receipt()
		from erpnext.stock.doctype.batch.batch import split_batch

		new_batch = split_batch(receipt.items[0].batch_no, 'ITEM-BATCH-1', receipt.items[0].warehouse, 22)

		self.assertEquals(get_batch_qty(receipt.items[0].batch_no, receipt.items[0].warehouse), 78)
		self.assertEquals(get_batch_qty(new_batch, receipt.items[0].warehouse), 22)

	def test_get_batch_qty(self):
		'''Test getting batch quantities by batch_numbers, item_code or warehouse'''
		self.make_batch_item('ITEM-BATCH-2')
		self.make_new_batch_and_entry('ITEM-BATCH-2', 'batch a', '_Test Warehouse - _TC')
		self.make_new_batch_and_entry('ITEM-BATCH-2', 'batch b', '_Test Warehouse - _TC')

		self.assertEquals(get_batch_qty(item_code = 'ITEM-BATCH-2', warehouse = '_Test Warehouse - _TC'),
			[{'batch_no': u'batch a', 'qty': 90.0}, {'batch_no': u'batch b', 'qty': 90.0}])

		self.assertEquals(get_batch_qty('batch a', '_Test Warehouse - _TC'), 90)

	@classmethod
	def make_new_batch_and_entry(cls, item_name, batch_name, warehouse):
		'''Make a new stock entry for given target warehouse and batch name of item'''

		if not frappe.db.exists("Batch", batch_name):
			batch = frappe.get_doc(dict(
				doctype = 'Batch',
				item = item_name,
				batch_id = batch_name
			)).insert(ignore_permissions=True)
			batch.submit()

		stock_entry = frappe.get_doc(dict(
			doctype = 'Stock Entry',
			purpose = 'Material Receipt',
			company = '_Test Company',
			items = [
				dict(
					item_code = item_name,
					qty = 90,
					t_warehouse = warehouse,
					cost_center = 'Main - _TC',
					rate = 10,
					batch_no = batch_name,
					allow_zero_valuation_rate = 1
				)
			]
		)).insert()
		stock_entry.submit()
