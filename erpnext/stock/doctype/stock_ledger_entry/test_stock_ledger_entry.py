# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

# test_records = frappe.get_test_records('Stock Ledger Entry')

class TestStockLedgerEntry(unittest.TestCase):

	def test_selling_rate_baseson_sales_invoice(self):
		test_record = frappe.get_test_records('Sales Invoice')[1]
		doc = frappe.copy_doc(test_record)
		doc.update_stock = 1
		doc.save()
		doc.submit()
		for item in doc.items:
			self.assertTrue(frappe.db.get_value('Stock Ledger Entry', {'voucher_detail_no': item.name}, 'selling_rate') == item.base_rate)

		doc.cancel()
		doc.delete()

	def test_selling_rate_baseson_delivery_note(self):
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note

		doc = create_delivery_note()

		for item in doc.items:
			self.assertTrue(frappe.db.get_value('Stock Ledger Entry', {'voucher_detail_no': item.name}, 'selling_rate') == item.base_rate)

		doc.cancel()
		doc.delete()


	def test_selling_rate_baseson_purchase_receipt(self):
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		doc = make_purchase_receipt()

		for item in doc.items:
			self.assertTrue(frappe.db.get_value('Stock Ledger Entry', {'voucher_detail_no': item.name}, 'selling_rate') == 0)

		doc.cancel()
		doc.delete()
