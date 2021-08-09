# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from erpnext.stock.doctype.item.item import DataValidationError
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.e_commerce.doctype.website_item.website_item import make_website_item
from erpnext.controllers.item_variant import create_variant
from erpnext.e_commerce.doctype.e_commerce_settings.test_e_commerce_settings import setup_e_commerce_settings
from erpnext.e_commerce.shopping_cart.product_info import get_product_info_for_website

WEBITEM_DESK_TESTS = ("test_website_item_desk_item_sync", "test_publish_variant_and_template")
WEBITEM_PRICE_TESTS = ('test_website_item_price_for_logged_in_user', 'test_website_item_price_for_guest_user')

class TestWebsiteItem(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		setup_e_commerce_settings({
			"company": "_Test Company",
			"enabled": 1,
			"default_customer_group": "_Test Customer Group",
			"price_list": "_Test Price List India"
		})

	def setUp(self):
		if self._testMethodName in WEBITEM_DESK_TESTS:
			make_item("Test Web Item", {
				"has_variant": 1,
				"variant_based_on": "Item Attribute",
				"attributes": [
					{
						"attribute": "Test Size"
					}
				]
			})
		elif self._testMethodName in WEBITEM_PRICE_TESTS:
			self.create_regular_web_item()
			make_web_item_price(item_code="Test Mobile Phone")
			make_web_pricing_rule(
				title="Test Pricing Rule for Test Mobile Phone",
				item_code="Test Mobile Phone",
				selling=1)

	def tearDown(self):
		if self._testMethodName in WEBITEM_DESK_TESTS:
			frappe.get_doc("Item", "Test Web Item").delete()
		elif self._testMethodName in WEBITEM_PRICE_TESTS:
			frappe.delete_doc("Pricing Rule", "Test Pricing Rule for Test Mobile Phone")
			frappe.get_cached_doc("Item Price", {"item_code": "Test Mobile Phone"}).delete()
			frappe.get_cached_doc("Website Item", {"item_code": "Test Mobile Phone"}).delete()


	def test_index_creation(self):
		"Check if index is getting created in db."
		from erpnext.e_commerce.doctype.website_item.website_item import on_doctype_update
		on_doctype_update()

		indices = frappe.db.sql("show index from `tabWebsite Item`", as_dict=1)
		expected_columns = {"route", "item_group", "brand"}
		for index in indices:
			expected_columns.discard(index.get("Column_name"))

		if expected_columns:
			self.fail(f"Expected db index on these columns: {', '.join(expected_columns)}")

	def test_website_item_desk_item_sync(self):
		"Check creation/updation/deletion of Website Item and its impact on Item master."
		web_item = None
		item = make_item("Test Web Item") # will return item if exists
		try:
			web_item = make_website_item(item, save=False)
			web_item.save()
		except Exception:
			self.fail(f"Error while creating website item for {item}")

		# check if website item was created
		self.assertTrue(bool(web_item))
		self.assertTrue(bool(web_item.route))

		item.reload()
		self.assertEqual(web_item.published, 1)
		self.assertEqual(item.published_in_website, 1) # check if item was back updated
		self.assertEqual(web_item.item_group, item.item_group)

		# check if changing item data changes it in website item
		item.item_name = "Test Web Item 1"
		item.stock_uom = "Unit"
		item.save()
		web_item.reload()
		self.assertEqual(web_item.item_name, item.item_name)
		self.assertEqual(web_item.stock_uom, item.stock_uom)

		# check if disabling item unpublished website item
		item.disabled = 1
		item.save()
		web_item.reload()
		self.assertEqual(web_item.published, 0)

		# check if website item deletion, unpublishes desk item
		web_item.delete()
		item.reload()
		self.assertEqual(item.published_in_website, 0)

	def test_publish_variant_and_template(self):
		"Check if template is published on publishing variant."
		template = frappe.get_doc("Item", "Test Web Item")
		variant = create_variant("Test Web Item", {"Test Size": "Large"})
		variant.save()

		# check if template is not published
		self.assertIsNone(frappe.db.exists("Website Item", {"item_code": variant.variant_of}))

		variant_web_item = make_website_item(variant, save=False)
		variant_web_item.save()

		# check if template is published
		try:
			template_web_item = frappe.get_doc("Website Item", {"item_code": variant.variant_of})
		except DoesNotExistError:
			self.fail(f"Template of {variant.item_code}, {variant.variant_of} not published")

		# teardown
		variant_web_item.delete()
		template_web_item.delete()
		variant.delete()

	def test_impact_on_merging_items(self):
		"Check if merging items is blocked if old and new items both have website items"
		first_item = make_item("Test First Item")
		second_item = make_item("Test Second Item")

		first_web_item = make_website_item(first_item, save=False)
		first_web_item.save()
		second_web_item = make_website_item(second_item, save=False)
		second_web_item.save()

		with self.assertRaises(DataValidationError):
			frappe.rename_doc("Item", "Test First Item", "Test Second Item", merge=True)

		# tear down
		second_web_item.delete()
		first_web_item.delete()
		second_item.delete()
		first_item.delete()

	# Website Item Portal Tests Begin

	def test_website_item_breadcrumbs(self):
		"Check if breadcrumbs include homepage, product listing navigation page, parent item group(s) and item group."
		from erpnext.setup.doctype.item_group.item_group import get_parent_item_groups

		item_code = "Test Breadcrumb Item"
		item = make_item(item_code, {
			"item_group": "_Test Item Group B - 1",
		})

		if not frappe.db.exists("Website Item", {"item_code": item_code}):
			web_item = make_website_item(item, save=False)
			web_item.save()
		else:
			web_item = frappe.get_cached_doc("Website Item", {"item_code": item_code})

		frappe.db.set_value("Item Group", "_Test Item Group B - 1", "show_in_website", 1)
		frappe.db.set_value("Item Group", "_Test Item Group B", "show_in_website", 1)

		breadcrumbs = get_parent_item_groups(item.item_group)

		self.assertEqual(breadcrumbs[0]["name"], "Home")
		self.assertEqual(breadcrumbs[1]["name"], "Shop by Category")
		self.assertEqual(breadcrumbs[2]["name"], "_Test Item Group B") # parent item group
		self.assertEqual(breadcrumbs[3]["name"], "_Test Item Group B - 1")

		# tear down
		web_item.delete()
		item.delete()

	def test_website_item_price_for_logged_in_user(self):
		"Check if price details are fetched correctly while logged in."
		item_code = "Test Mobile Phone"

		# show price in e commerce settings
		setup_e_commerce_settings({"show_price": 1})

		# price and pricing rule added via setUp

		# check if price and slashed price is fetched correctly
		frappe.local.shopping_cart_settings = None
		data = get_product_info_for_website(item_code, skip_quotation_creation=True)
		self.assertTrue(bool(data.product_info["price"]))

		price_object = data.product_info["price"]
		self.assertEqual(price_object.get("discount_percent"), 10)
		self.assertEqual(price_object.get("price_list_rate"), 900)
		self.assertEqual(price_object.get("formatted_mrp"), "₹ 1,000.00")
		self.assertEqual(price_object.get("formatted_price"), "₹ 900.00")
		self.assertEqual(price_object.get("formatted_discount_percent"), "10%")

		# disable show price
		setup_e_commerce_settings({"show_price": 0})

		# price should not be fetched
		frappe.local.shopping_cart_settings = None
		data = get_product_info_for_website(item_code, skip_quotation_creation=True)
		self.assertFalse(bool(data.product_info["price"]))

		# tear down
		frappe.set_user("Administrator")

	def test_website_item_price_for_guest_user(self):
		"Check if price details are fetched correctly for guest user."
		item_code = "Test Mobile Phone"

		# show price for guest user in e commerce settings
		setup_e_commerce_settings({
			"show_price": 1,
			"hide_price_for_guest": 0
		})

		# price and pricing rule added via setUp

		# switch to guest user
		frappe.set_user("Guest")

		# price should be fetched
		frappe.local.shopping_cart_settings = None
		data = get_product_info_for_website(item_code, skip_quotation_creation=True)
		self.assertTrue(bool(data.product_info["price"]))

		price_object = data.product_info["price"]
		self.assertEqual(price_object.get("discount_percent"), 10)
		self.assertEqual(price_object.get("price_list_rate"), 900)

		# hide price for guest user
		frappe.set_user("Administrator")
		setup_e_commerce_settings({"hide_price_for_guest": 1})
		frappe.set_user("Guest")

		# price should not be fetched
		frappe.local.shopping_cart_settings = None
		data = get_product_info_for_website(item_code, skip_quotation_creation=True)
		self.assertFalse(bool(data.product_info["price"]))

		# tear down
		frappe.set_user("Administrator")

	def test_website_item_stock_when_out_of_stock(self):
		"""
			Check if stock details are fetched correctly for empty inventory when:
			1) Showing stock availability enabled:
				- Warehouse unset
				- Warehouse set
			2) Showing stock availability disabled
		"""
		item_code = "Test Mobile Phone"
		self.create_regular_web_item()
		setup_e_commerce_settings({"show_stock_availability": 1})

		frappe.local.shopping_cart_settings = None
		data = get_product_info_for_website(item_code, skip_quotation_creation=True)

		# check if stock details are fetched and item not in stock without warehouse set
		self.assertFalse(bool(data.product_info["in_stock"]))
		self.assertFalse(bool(data.product_info["stock_qty"]))

		# set warehouse
		frappe.db.set_value("Website Item", {"item_code": item_code}, "website_warehouse", "_Test Warehouse - _TC")

		# check if stock details are fetched and item not in stock with warehouse set
		data = get_product_info_for_website(item_code, skip_quotation_creation=True)
		self.assertFalse(bool(data.product_info["in_stock"]))
		self.assertEqual(data.product_info["stock_qty"][0][0], 0)

		# disable show stock availability
		setup_e_commerce_settings({"show_stock_availability": 0})
		frappe.local.shopping_cart_settings = None
		data = get_product_info_for_website(item_code, skip_quotation_creation=True)

		# check if stock detail attributes are not fetched if stock availability is hidden
		self.assertIsNone(data.product_info.get("in_stock"))
		self.assertIsNone(data.product_info.get("stock_qty"))
		self.assertIsNone(data.product_info.get("show_stock_qty"))

		# tear down
		frappe.get_cached_doc("Website Item", {"item_code": "Test Mobile Phone"}).delete()

	def test_website_item_stock_when_in_stock(self):
		"""
			Check if stock details are fetched correctly for available inventory when:
			1) Showing stock availability enabled:
				- Warehouse set
				- Warehouse unset
			2) Showing stock availability disabled
		"""
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		item_code = "Test Mobile Phone"
		self.create_regular_web_item()
		setup_e_commerce_settings({"show_stock_availability": 1})

		# set warehouse
		frappe.db.set_value("Website Item", {"item_code": item_code}, "website_warehouse", "_Test Warehouse - _TC")

		# stock up item
		stock_entry = make_stock_entry(item_code=item_code, target="_Test Warehouse - _TC", qty=2, rate=100)

		# check if stock details are fetched and item is in stock with warehouse set
		data = get_product_info_for_website(item_code, skip_quotation_creation=True)
		self.assertTrue(bool(data.product_info["in_stock"]))
		self.assertEqual(data.product_info["stock_qty"][0][0], 2)

		# unset warehouse
		frappe.db.set_value("Website Item", {"item_code": item_code}, "website_warehouse", "")

		# check if stock details are fetched and item not in stock without warehouse set
		# (even though it has stock in some warehouse)
		data = get_product_info_for_website(item_code, skip_quotation_creation=True)
		self.assertFalse(bool(data.product_info["in_stock"]))
		self.assertFalse(bool(data.product_info["stock_qty"]))

		# disable show stock availability
		setup_e_commerce_settings({"show_stock_availability": 0})
		frappe.local.shopping_cart_settings = None
		data = get_product_info_for_website(item_code, skip_quotation_creation=True)

		# check if stock detail attributes are not fetched if stock availability is hidden
		self.assertIsNone(data.product_info.get("in_stock"))
		self.assertIsNone(data.product_info.get("stock_qty"))
		self.assertIsNone(data.product_info.get("show_stock_qty"))

		# tear down
		stock_entry.cancel()
		frappe.get_cached_doc("Website Item", {"item_code": "Test Mobile Phone"}).delete()


	def create_regular_web_item(self):
		"Create Regular Item and Website Item."
		item_code = "Test Mobile Phone"
		item = make_item(item_code)

		if not frappe.db.exists("Website Item", {"item_code": item_code}):
			web_item = make_website_item(item, save=False)
			web_item.save()

def make_web_item_price(**kwargs):
	item_code = kwargs.get("item_code")
	if not item_code:
		return

	if not frappe.db.exists("Item Price", {"item_code": item_code}):
		item_price = frappe.get_doc({
			"doctype": "Item Price",
			"item_code": item_code,
			"price_list": kwargs.get("price_list") or "_Test Price List India",
			"price_list_rate": kwargs.get("price_list_rate") or 1000
		})
		item_price.insert()
	else:
		item_price = frappe.get_cached_doc("Item Price", {"item_code": item_code})

	return item_price

def make_web_pricing_rule(**kwargs):
	title = kwargs.get("title")
	if not title:
		return

	if not frappe.db.exists("Pricing Rule", title):
		pricing_rule = frappe.get_doc({
			"doctype": "Pricing Rule",
			"title": title,
			"apply_on": kwargs.get("apply_on") or "Item Code",
			"items": [{
				"item_code": kwargs.get("item_code")
			}],
			"selling": kwargs.get("selling") or 0,
			"buying": kwargs.get("buying") or 0,
			"rate_or_discount": kwargs.get("rate_or_discount") or "Discount Percentage",
			"discount_percentage": kwargs.get("discount_percentage") or 10,
			"company": kwargs.get("company") or "_Test Company",
			"currency": kwargs.get("currency") or "INR",
			"for_price_list": kwargs.get("price_list") or "_Test Price List India"
		})
		pricing_rule.insert()
	else:
		pricing_rule = frappe.get_doc("Pricing Rule", {"title": title})

	return pricing_rule