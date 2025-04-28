# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
<<<<<<< HEAD
from frappe.tests import IntegrationTestCase
from frappe.tests.utils import make_test_records_for_doctype

from erpnext.stock.doctype.item_price.item_price import ItemPriceDuplicateItem
from erpnext.stock.get_item_details import ItemDetailsCtx, get_price_list_rate_for


class TestItemPrice(IntegrationTestCase):
=======
from frappe.test_runner import make_test_records_for_doctype
from frappe.tests.utils import FrappeTestCase

from erpnext.stock.doctype.item_price.item_price import ItemPriceDuplicateItem
from erpnext.stock.get_item_details import get_price_list_rate_for, process_args


class TestItemPrice(FrappeTestCase):
>>>>>>> 7c4cf3e834 (Favicon.svg)
	def setUp(self):
		super().setUp()
		frappe.db.sql("delete from `tabItem Price`")
		make_test_records_for_doctype("Item Price", force=True)

	def test_template_item_price(self):
		from erpnext.stock.doctype.item.test_item import make_item

		item = make_item(
			"Test Template Item 1",
			{
				"has_variants": 1,
				"variant_based_on": "Manufacturer",
			},
		)

		doc = frappe.get_doc(
			{
				"doctype": "Item Price",
				"price_list": "_Test Price List",
				"item_code": item.name,
				"price_list_rate": 100,
			}
		)

		self.assertRaises(frappe.ValidationError, doc.save)

	def test_duplicate_item(self):
<<<<<<< HEAD
		doc = frappe.copy_doc(self.globalTestRecords["Item Price"][0])
=======
		doc = frappe.copy_doc(test_records[0])
>>>>>>> 7c4cf3e834 (Favicon.svg)
		self.assertRaises(ItemPriceDuplicateItem, doc.save)

	def test_addition_of_new_fields(self):
		# Based on https://github.com/frappe/erpnext/issues/8456
		test_fields_existance = [
			"supplier",
			"customer",
			"uom",
			"lead_time_days",
			"packing_unit",
			"valid_from",
			"valid_upto",
			"note",
		]
<<<<<<< HEAD
		doc_fields = frappe.copy_doc(self.globalTestRecords["Item Price"][1]).__dict__.keys()
=======
		doc_fields = frappe.copy_doc(test_records[1]).__dict__.keys()
>>>>>>> 7c4cf3e834 (Favicon.svg)

		for test_field in test_fields_existance:
			self.assertTrue(test_field in doc_fields)

	def test_dates_validation_error(self):
<<<<<<< HEAD
		doc = frappe.copy_doc(self.globalTestRecords["Item Price"][1])
=======
		doc = frappe.copy_doc(test_records[1])
>>>>>>> 7c4cf3e834 (Favicon.svg)
		# Enter invalid dates valid_from  >= valid_upto
		doc.valid_from = "2017-04-20"
		doc.valid_upto = "2017-04-17"
		# Valid Up To Date can not be less/equal than Valid From Date
		self.assertRaises(frappe.ValidationError, doc.save)

	def test_price_in_a_qty(self):
		# Check correct price at this quantity
<<<<<<< HEAD
		doc = frappe.copy_doc(self.globalTestRecords["Item Price"][2])

		ctx = ItemDetailsCtx(
			{
				"price_list": doc.price_list,
				"customer": doc.customer,
				"uom": "_Test UOM",
				"transaction_date": "2017-04-18",
				"qty": 10,
			}
		)

		price = get_price_list_rate_for(ctx, doc.item_code)
=======
		doc = frappe.copy_doc(test_records[2])

		args = {
			"price_list": doc.price_list,
			"customer": doc.customer,
			"uom": "_Test UOM",
			"transaction_date": "2017-04-18",
			"qty": 10,
		}

		price = get_price_list_rate_for(process_args(args), doc.item_code)
>>>>>>> 7c4cf3e834 (Favicon.svg)
		self.assertEqual(price, 20.0)

	def test_price_with_no_qty(self):
		# Check correct price when no quantity
<<<<<<< HEAD
		doc = frappe.copy_doc(self.globalTestRecords["Item Price"][2])
		ctx = ItemDetailsCtx(
			{
				"price_list": doc.price_list,
				"customer": doc.customer,
				"uom": "_Test UOM",
				"transaction_date": "2017-04-18",
			}
		)

		price = get_price_list_rate_for(ctx, doc.item_code)
=======
		doc = frappe.copy_doc(test_records[2])
		args = {
			"price_list": doc.price_list,
			"customer": doc.customer,
			"uom": "_Test UOM",
			"transaction_date": "2017-04-18",
		}

		price = get_price_list_rate_for(args, doc.item_code)
>>>>>>> 7c4cf3e834 (Favicon.svg)
		self.assertEqual(price, None)

	def test_prices_at_date(self):
		# Check correct price at first date
<<<<<<< HEAD
		doc = frappe.copy_doc(self.globalTestRecords["Item Price"][2])

		ctx = ItemDetailsCtx(
			{
				"price_list": doc.price_list,
				"customer": "_Test Customer",
				"uom": "_Test UOM",
				"transaction_date": "2017-04-18",
				"qty": 7,
			}
		)

		price = get_price_list_rate_for(ctx, doc.item_code)
=======
		doc = frappe.copy_doc(test_records[2])

		args = {
			"price_list": doc.price_list,
			"customer": "_Test Customer",
			"uom": "_Test UOM",
			"transaction_date": "2017-04-18",
			"qty": 7,
		}

		price = get_price_list_rate_for(args, doc.item_code)
>>>>>>> 7c4cf3e834 (Favicon.svg)
		self.assertEqual(price, 20)

	def test_prices_at_invalid_date(self):
		# Check correct price at invalid date
<<<<<<< HEAD
		doc = frappe.copy_doc(self.globalTestRecords["Item Price"][3])

		ctx = ItemDetailsCtx(
			{
				"price_list": doc.price_list,
				"qty": 7,
				"uom": "_Test UOM",
				"transaction_date": "01-15-2019",
			}
		)

		price = get_price_list_rate_for(ctx, doc.item_code)
=======
		doc = frappe.copy_doc(test_records[3])

		args = {
			"price_list": doc.price_list,
			"qty": 7,
			"uom": "_Test UOM",
			"transaction_date": "01-15-2019",
		}

		price = get_price_list_rate_for(args, doc.item_code)
>>>>>>> 7c4cf3e834 (Favicon.svg)
		self.assertEqual(price, None)

	def test_prices_outside_of_date(self):
		# Check correct price when outside of the date
<<<<<<< HEAD
		doc = frappe.copy_doc(self.globalTestRecords["Item Price"][4])

		ctx = ItemDetailsCtx(
			{
				"price_list": doc.price_list,
				"customer": "_Test Customer",
				"uom": "_Test UOM",
				"transaction_date": "2017-04-25",
				"qty": 7,
			}
		)

		price = get_price_list_rate_for(ctx, doc.item_code)
=======
		doc = frappe.copy_doc(test_records[4])

		args = {
			"price_list": doc.price_list,
			"customer": "_Test Customer",
			"uom": "_Test UOM",
			"transaction_date": "2017-04-25",
			"qty": 7,
		}

		price = get_price_list_rate_for(args, doc.item_code)
>>>>>>> 7c4cf3e834 (Favicon.svg)
		self.assertEqual(price, None)

	def test_lowest_price_when_no_date_provided(self):
		# Check lowest price when no date provided
<<<<<<< HEAD
		doc = frappe.copy_doc(self.globalTestRecords["Item Price"][1])

		ctx = ItemDetailsCtx(
			{
				"price_list": doc.price_list,
				"uom": "_Test UOM",
				"qty": 7,
			}
		)

		price = get_price_list_rate_for(ctx, doc.item_code)
		self.assertEqual(price, 10)

	def test_invalid_item(self):
		doc = frappe.copy_doc(self.globalTestRecords["Item Price"][1])
=======
		doc = frappe.copy_doc(test_records[1])

		args = {
			"price_list": doc.price_list,
			"uom": "_Test UOM",
			"qty": 7,
		}

		price = get_price_list_rate_for(args, doc.item_code)
		self.assertEqual(price, 10)

	def test_invalid_item(self):
		doc = frappe.copy_doc(test_records[1])
>>>>>>> 7c4cf3e834 (Favicon.svg)
		# Enter invalid item code
		doc.item_code = "This is not an item code"
		# Valid item codes must already exist
		self.assertRaises(frappe.ValidationError, doc.save)

	def test_invalid_price_list(self):
<<<<<<< HEAD
		doc = frappe.copy_doc(self.globalTestRecords["Item Price"][1])
=======
		doc = frappe.copy_doc(test_records[1])
>>>>>>> 7c4cf3e834 (Favicon.svg)
		# Check for invalid price list
		doc.price_list = "This is not a price list"
		# Valid price list must already exist
		self.assertRaises(frappe.ValidationError, doc.save)

	def test_empty_duplicate_validation(self):
		# Check if none/empty values are not compared during insert validation
<<<<<<< HEAD
		doc = frappe.copy_doc(self.globalTestRecords["Item Price"][2])
=======
		doc = frappe.copy_doc(test_records[2])
>>>>>>> 7c4cf3e834 (Favicon.svg)
		doc.customer = None
		doc.price_list_rate = 21
		doc.insert()

<<<<<<< HEAD
		ctx = ItemDetailsCtx(
			{
				"price_list": doc.price_list,
				"uom": "_Test UOM",
				"transaction_date": "2017-04-18",
				"qty": 7,
			}
		)

		price = get_price_list_rate_for(ctx, doc.item_code)
		frappe.db.rollback()

		self.assertEqual(price, 21)
=======
		args = {
			"price_list": doc.price_list,
			"uom": "_Test UOM",
			"transaction_date": "2017-04-18",
			"qty": 7,
		}

		price = get_price_list_rate_for(args, doc.item_code)
		frappe.db.rollback()

		self.assertEqual(price, 21)


test_records = frappe.get_test_records("Item Price")
>>>>>>> 7c4cf3e834 (Favicon.svg)
