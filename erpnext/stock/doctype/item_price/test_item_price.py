# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe.utils import add_days, today

from erpnext.stock.doctype.item_price.item_price import ItemPriceDuplicateItem
from erpnext.stock.get_item_details import get_price_list_rate_for
from erpnext.tests.utils import ERPNextTestSuite


class TestItemPrice(ERPNextTestSuite):
	def setUp(self):
		self.load_test_records("Item Price")

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
		doc = frappe.copy_doc(self.globalTestRecords["Item Price"][0])
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
		doc_fields = frappe.copy_doc(self.globalTestRecords["Item Price"][1]).__dict__.keys()

		for test_field in test_fields_existance:
			self.assertIn(test_field, doc_fields)

	def test_dates_validation_error(self):
		doc = frappe.copy_doc(self.globalTestRecords["Item Price"][1])
		# Enter invalid dates valid_from  >= valid_upto
		doc.valid_from = "2017-04-20"
		doc.valid_upto = "2017-04-17"
		# Valid Up To Date can not be less/equal than Valid From Date
		self.assertRaises(frappe.ValidationError, doc.save)

	def test_price_in_a_qty(self):
		# Check correct price at this quantity
		doc = frappe.copy_doc(self.globalTestRecords["Item Price"][2])

		ctx = frappe._dict(
			{
				"price_list": doc.price_list,
				"customer": doc.customer,
				"uom": "_Test UOM",
				"transaction_date": "2017-04-18",
				"qty": 10,
			}
		)

		price = get_price_list_rate_for(ctx, doc.item_code)
		self.assertEqual(price, 20.0)

	def test_price_with_no_qty(self):
		# Check correct price when no quantity
		doc = frappe.copy_doc(self.globalTestRecords["Item Price"][2])
		ctx = frappe._dict(
			{
				"price_list": doc.price_list,
				"customer": doc.customer,
				"uom": "_Test UOM",
				"transaction_date": "2017-04-18",
			}
		)

		price = get_price_list_rate_for(ctx, doc.item_code)
		self.assertEqual(price, None)

	def test_prices_at_date(self):
		# Check correct price at first date
		doc = frappe.copy_doc(self.globalTestRecords["Item Price"][2])

		ctx = frappe._dict(
			{
				"price_list": doc.price_list,
				"customer": "_Test Customer",
				"uom": "_Test UOM",
				"transaction_date": "2017-04-18",
				"qty": 7,
			}
		)

		price = get_price_list_rate_for(ctx, doc.item_code)
		self.assertEqual(price, 20)

	def test_prices_at_invalid_date(self):
		# Check correct price at invalid date
		doc = frappe.copy_doc(self.globalTestRecords["Item Price"][3])

		ctx = frappe._dict(
			{
				"price_list": doc.price_list,
				"qty": 7,
				"uom": "_Test UOM",
				"transaction_date": "01-15-2019",
			}
		)

		price = get_price_list_rate_for(ctx, doc.item_code)
		self.assertEqual(price, None)

	def test_prices_outside_of_date(self):
		# Check correct price when outside of the date
		doc = frappe.copy_doc(self.globalTestRecords["Item Price"][4])

		ctx = frappe._dict(
			{
				"price_list": doc.price_list,
				"customer": "_Test Customer",
				"uom": "_Test UOM",
				"transaction_date": "2017-04-25",
				"qty": 7,
			}
		)

		price = get_price_list_rate_for(ctx, doc.item_code)
		self.assertEqual(price, None)

	def test_lowest_price_when_no_date_provided(self):
		# Check lowest price when no date provided
		doc = frappe.copy_doc(self.globalTestRecords["Item Price"][1])

		ctx = frappe._dict(
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
		# Enter invalid item code
		doc.item_code = "This is not an item code"
		# Valid item codes must already exist
		self.assertRaises(frappe.ValidationError, doc.save)

	def test_invalid_price_list(self):
		doc = frappe.copy_doc(self.globalTestRecords["Item Price"][1])
		# Check for invalid price list
		doc.price_list = "This is not a price list"
		# Valid price list must already exist
		self.assertRaises(frappe.ValidationError, doc.save)

	def test_empty_duplicate_validation(self):
		# Check if none/empty values are not compared during insert validation
		doc = frappe.copy_doc(self.globalTestRecords["Item Price"][2])
		doc.customer = None
		doc.price_list_rate = 21
		doc.insert()

		ctx = frappe._dict(
			{
				"price_list": doc.price_list,
				"uom": "_Test UOM",
				"transaction_date": "2017-04-18",
				"qty": 7,
			}
		)

		price = get_price_list_rate_for(ctx, doc.item_code)

		self.assertEqual(price, 21)

	def make_price(self, item_code, rate, valid_from, **kwargs):
		return frappe.get_doc(
			{
				"doctype": "Item Price",
				"price_list": "_Test Price List",
				"item_code": item_code,
				"price_list_rate": rate,
				"valid_from": valid_from,
				**kwargs,
			}
		).insert()

	def test_customer_price_wins_over_newer_general_price(self):
		from erpnext.stock.doctype.item.test_item import make_item

		item_code = make_item(properties={"is_stock_item": 1}).name
		self.make_price(item_code, 900, add_days(today(), -200), customer="_Test Customer")
		self.make_price(item_code, 1000, add_days(today(), -30))

		ctx = frappe._dict(
			price_list="_Test Price List",
			customer="_Test Customer",
			uom=frappe.db.get_value("Item", item_code, "stock_uom"),
			transaction_date=today(),
			qty=1,
		)
		self.assertEqual(get_price_list_rate_for(ctx, item_code), 900)

	def test_supplier_price_wins_over_newer_general_price(self):
		from erpnext.stock.doctype.item.test_item import make_item

		item_code = make_item(properties={"is_stock_item": 1}).name
		price_list = "_Test Buying Price List"
		self.make_price(
			item_code, 800, add_days(today(), -200), price_list=price_list, supplier="_Test Supplier"
		)
		self.make_price(item_code, 1000, add_days(today(), -30), price_list=price_list)

		ctx = frappe._dict(
			price_list=price_list,
			supplier="_Test Supplier",
			uom=frappe.db.get_value("Item", item_code, "stock_uom"),
			transaction_date=today(),
			qty=1,
		)
		self.assertEqual(get_price_list_rate_for(ctx, item_code), 800)

	def test_batch_price_wins_over_newer_general_price(self):
		from erpnext.stock.doctype.item.test_item import make_item

		item_code = make_item(properties={"is_stock_item": 1, "has_batch_no": 1, "create_new_batch": 0}).name
		batch_no = (
			frappe.get_doc(
				{"doctype": "Batch", "batch_id": frappe.generate_hash(length=10), "item": item_code}
			)
			.insert()
			.name
		)
		self.make_price(item_code, 700, add_days(today(), -200), batch_no=batch_no)
		self.make_price(item_code, 1000, add_days(today(), -30))

		ctx = frappe._dict(
			price_list="_Test Price List",
			batch_no=batch_no,
			uom=frappe.db.get_value("Item", item_code, "stock_uom"),
			transaction_date=today(),
			qty=1,
		)
		self.assertEqual(get_price_list_rate_for(ctx, item_code), 700)

	def test_price_falls_back_when_packing_unit_does_not_fit(self):
		from erpnext.stock.doctype.item.test_item import make_item

		item_code = make_item(properties={"is_stock_item": 1}).name
		self.make_price(item_code, 100, add_days(today(), -60))
		self.make_price(item_code, 90, add_days(today(), -5), packing_unit=12)

		ctx = frappe._dict(
			price_list="_Test Price List",
			uom=frappe.db.get_value("Item", item_code, "stock_uom"),
			transaction_date=today(),
		)
		self.assertEqual(get_price_list_rate_for(ctx.copy().update(qty=24), item_code), 90)
		self.assertEqual(get_price_list_rate_for(ctx.copy().update(qty=5), item_code), 100)
