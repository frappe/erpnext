# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import unittest
import frappe
from erpnext.stock.get_item_details import get_price_list_rate_for


class TestItem(unittest.TestCase):
	def test_addition_of_new_fields(self):
		# Based on https://github.com/frappe/erpnext/issues/8456
		test_fields_existance = [
			'disable', 'customer', 'uom', 'min_qty', 'lead_time_days',
			'packing_unit', 'valid_from', 'valid_upto', 'note'
		]
		doc_fields = frappe.copy_doc(test_records[1]).__dict__.keys()

		for test_field in test_fields_existance:
			self.assertTrue(test_field in doc_fields)

	def test_dates_validation_error(self):
		doc = frappe.copy_doc(test_records[1])
		# Enter invalid dates valid_from  >= valid_upto
		doc.valid_from = "2017-04-20"
		doc.valid_upto = "2017-04-17"
		# Valid Upto Date can not be less/equal than Valid From Date
		self.assertRaises(frappe.ValidationError, doc.save)

	def test_invalid_item(self):
		doc = frappe.copy_doc(test_records[1])
		# Enter invalid item code
		doc.item_code = "This is not an item code"
		# Valid item codes must already exist
		self.assertRaises(frappe.ValidationError, doc.save)

	def test_price_list(self):
		doc = frappe.copy_doc(test_records[1])
		# Check for invalid price list
		doc.price_list = "This is not a price list"
		# Valid price list must already exist
		self.assertRaises(frappe.ValidationError, doc.save)
		
		
		# Check for disabled price list
		doc = frappe.copy_doc(test_records[1])
		# Enter invalid price list
		pr = frappe.get_doc("Price List", doc.price_list)
		pr.enabled = 0
		pr.save()
		
		doc.price_list = pr.name
		# Valid price list must already exist
		self.assertRaises(frappe.ValidationError, doc.save)
		pr.enabled = 1
		pr.save()
		
	def test_price(self):
		doc = frappe.copy_doc(test_records[0])
		doc.min_qty = 5
		doc.save()
		
		#Check correct price at this quantity
		price = get_price_list_rate_for(doc.price_list, doc.item_code, doc.min_qty)
		self.assertEqual(price, doc.price_list_rate)
		
		#Check correct price at this quantity + 1
		price = get_price_list_rate_for(doc.price_list, doc.item_code, doc.min_qty + 1)
		self.assertEqual(price, doc.price_list_rate)
		
		#Check correct price at this quantity - 1
		price = get_price_list_rate_for(doc.price_list, doc.item_code, doc.min_qty - 1)
		self.assertEqual(price, None)
		
test_records = frappe.get_test_records('Item Price')
