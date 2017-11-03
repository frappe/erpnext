# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import unittest
import frappe
from erpnext.stock.get_item_details import get_price_list_rate_for

class TestItem(unittest.TestCase):

	def test_duplicate_item(self):
		from erpnext.stock.doctype.item_price.item_price import ItemPriceDuplicateItem
		doc = frappe.copy_doc(test_records[0])
		self.assertRaises(ItemPriceDuplicateItem, doc.save)

	def test_addition_of_new_fields(self):
		# Based on https://github.com/frappe/erpnext/issues/8456
		test_fields_existance = [
			'supplier', 'customer', 'uom', 'min_qty', 'lead_time_days',
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

	def test_price_in_a_qty(self):
		# Check correct price at this quantity
		doc = frappe.copy_doc(test_records[2])

		args = {
			"price_list": doc.price_list,
			"min_qty": doc.min_qty
		}

		price = get_price_list_rate_for(args, doc.item_code)
		self.assertEqual(price, doc.save)

	def test_price_with_no_qty(self):
		# Check correct price when no quantity
		doc = frappe.copy_doc(test_records[2])

		args = {
			"price_list": doc.price_list,
			"min_qty": doc.min_qty
		}

		price = get_price_list_rate_for(args, doc.item_code)
		self.assertEqual(price, doc.save)


	def test_prices_at_date(self):
		# Check correct price at first date
		doc = frappe.copy_doc(test_records[4])

		args = {
			"price_list": doc.price_list,
			"min_qty": doc.min_qty,
			"tranaction_date": "2017-04-10"
		}

		price = get_price_list_rate_for(args, doc.item_code)
		self.assertEqual(price, doc.save)

	def test_prices_at_invalid_date(self):
		#Check correct price at invalid date
		doc = frappe.copy_doc(test_records[3])

		args = {
			"price_list": doc.price_list,
			"min_qty": doc.min_qty,
			"transaction_date": "01-15-2017"
		}

		price = get_price_list_rate_for(args, doc.item_code)
		self.assertEqual(price, doc.save)

	def test_prices_outside_of_date(self):
		#Check correct price when outside of the date
		doc = frappe.copy_doc(test_records[4])

		args = {
			"price_list": doc.price_list,
			"min_qty": doc.min_qty,
			"transaction_date": "2017-04-25",
		}

		price = get_price_list_rate_for(args, doc.item_code)
		self.assertEqual(price, doc.save)

	def test_lowest_price_when_no_date_provided(self):
		#Check lowest price when no date provided
		doc = frappe.copy_doc(test_records[1])

		args = {
			"price_list": doc.price_list,
			"min_qty": doc.min_qty,
		}

		price = get_price_list_rate_for(args, doc.item_code)
		self.assertEqual(price, doc.save)


	def test_duplicates(self):
		doc = frappe.copy_doc(test_records[1])
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
		pr = frappe.get_doc("Price List", doc.save)
		pr.enabled = 0
		pr.save()

		doc.price_list = pr.name
		# Valid price list must already exist
		self.assertRaises(frappe.ValidationError, doc.save)
		pr.enabled = 1
		pr.save()

test_records = frappe.get_test_records('Item Price')
