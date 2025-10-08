# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import json

import frappe
from frappe.tests.utils import FrappeTestCase, change_settings

from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.controllers.sales_and_purchase_return import make_return_doc
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.get_item_details import get_item_details


class TestPricingRule(FrappeTestCase):
	def setUp(self):
		if frappe.db.get_single_value("Selling Settings", "validate_selling_price"):
			frappe.db.set_single_value("Selling Settings", "validate_selling_price", 0)
		delete_existing_pricing_rules()
		if "custom_crm" in frappe.get_installed_apps():
			setup_pricing_rule_data()

		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company
		from erpnext.stock.utils import get_or_create_fiscal_year

		create_company()
		get_or_create_fiscal_year("_Test Company")
		get_or_create_customer(customer_name="_Test Customer")

	def tearDown(self):
		delete_existing_pricing_rules()
		if frappe.db.get_single_value("Selling Settings", "validate_selling_price"):
			frappe.db.set_single_value("Selling Settings", "validate_selling_price", 0)

	def test_pricing_rule_for_discount(self):
		from frappe import MandatoryError

		from erpnext.stock.get_item_details import get_item_details

		test_record = {
			"doctype": "Pricing Rule",
			"title": "_Test Pricing Rule",
			"apply_on": "Item Code",
			"items": [{"item_code": "_Test Item"}],
			"currency": "USD",
			"selling": 1,
			"rate_or_discount": "Discount Percentage",
			"rate": 0,
			"discount_percentage": 10,
			"company": "_Test Company",
		}
		frappe.get_doc(test_record.copy()).insert()

		args = frappe._dict(
			{
				"item_code": "_Test Item",
				"company": "_Test Company",
				"price_list": "_Test Price List",
				"currency": "_Test Currency",
				"doctype": "Sales Order",
				"conversion_rate": 1,
				"price_list_currency": "_Test Currency",
				"plc_conversion_rate": 1,
				"order_type": "Sales",
				"customer": "_Test Customer",
				"name": None,
			}
		)
		details = get_item_details(args)
		self.assertEqual(details.get("discount_percentage"), 10)

		prule = frappe.get_doc(test_record.copy())
		prule.priority = 1
		prule.applicable_for = "Customer"
		prule.title = "_Test Pricing Rule for Customer"
		self.assertRaises(MandatoryError, prule.insert)

		prule.customer = "_Test Customer"
		prule.discount_percentage = 20
		prule.insert()
		details = get_item_details(args)
		self.assertEqual(details.get("discount_percentage"), 20)

		prule = frappe.get_doc(test_record.copy())
		prule.apply_on = "Item Group"
		prule.items = []
		prule.append("item_groups", {"item_group": "All Item Groups"})
		prule.title = "_Test Pricing Rule for Item Group"
		prule.discount_percentage = 15
		prule.insert()

		args.customer = "_Test Customer 1"
		details = get_item_details(args)
		self.assertEqual(details.get("discount_percentage"), 10)

		prule = frappe.get_doc(test_record.copy())
		prule.applicable_for = "Campaign"
		prule.campaign = "_Test Campaign"
		prule.title = "_Test Pricing Rule for Campaign"
		prule.discount_percentage = 5
		prule.priority = 8
		prule.insert()

		args.campaign = "_Test Campaign"
		details = get_item_details(args)
		self.assertEqual(details.get("discount_percentage"), 5)

		frappe.db.sql("update `tabPricing Rule` set priority=NULL where campaign='_Test Campaign'")
		from erpnext.accounts.doctype.pricing_rule.utils import MultiplePricingRuleConflict

		self.assertRaises(MultiplePricingRuleConflict, get_item_details, args)

		args.item_code = "_Test Item 2"
		details = get_item_details(args)
		self.assertEqual(details.get("discount_percentage"), 15)

	def test_pricing_rule_for_margin(self):
		from erpnext.stock.get_item_details import get_item_details

		test_record = {
			"doctype": "Pricing Rule",
			"title": "_Test Pricing Rule",
			"apply_on": "Item Code",
			"items": [
				{
					"item_code": "_Test FG Item 2",
				}
			],
			"selling": 1,
			"currency": "USD",
			"rate_or_discount": "Discount Percentage",
			"rate": 0,
			"margin_type": "Percentage",
			"margin_rate_or_amount": 10,
			"company": "_Test Company",
		}
		frappe.get_doc(test_record.copy()).insert()

		item_price = frappe.get_doc(
			{
				"doctype": "Item Price",
				"price_list": "_Test Price List 2",
				"item_code": "_Test FG Item 2",
				"price_list_rate": 100,
			}
		)

		item_price.insert(ignore_permissions=True)

		args = frappe._dict(
			{
				"item_code": "_Test FG Item 2",
				"company": "_Test Company",
				"price_list": "_Test Price List",
				"currency": "_Test Currency",
				"doctype": "Sales Order",
				"conversion_rate": 1,
				"price_list_currency": "_Test Currency",
				"plc_conversion_rate": 1,
				"order_type": "Sales",
				"customer": "_Test Customer",
				"name": None,
			}
		)
		details = get_item_details(args)
		self.assertEqual(details.get("margin_type"), "Percentage")
		self.assertEqual(details.get("margin_rate_or_amount"), 10)

	def test_mixed_conditions_for_item_group(self):
		for item in ["Mixed Cond Item 1", "Mixed Cond Item 2"]:
			make_item(item, {"item_group": "Products"})
			make_item_price(item, "_Test Price List", 100)

		test_record = {
			"doctype": "Pricing Rule",
			"title": "_Test Pricing Rule for Item Group",
			"apply_on": "Item Group",
			"item_groups": [
				{
					"item_group": "Products",
				},
				{
					"item_group": "_Test Item Group",
				},
			],
			"selling": 1,
			"mixed_conditions": 1,
			"currency": "USD",
			"rate_or_discount": "Discount Percentage",
			"discount_percentage": 10,
			"applicable_for": "Customer Group",
			"customer_group": "All Customer Groups",
			"company": "_Test Company",
		}
		frappe.get_doc(test_record.copy()).insert()

		args = frappe._dict(
			{
				"item_code": "Mixed Cond Item 1",
				"item_group": "Products",
				"company": "_Test Company",
				"price_list": "_Test Price List",
				"currency": "_Test Currency",
				"doctype": "Sales Order",
				"conversion_rate": 1,
				"price_list_currency": "_Test Currency",
				"plc_conversion_rate": 1,
				"order_type": "Sales",
				"customer": "_Test Customer",
				"customer_group": "_Test Customer Group",
				"name": None,
			}
		)
		details = get_item_details(args)
		self.assertEqual(details.get("discount_percentage"), 10)

	def test_pricing_rule_for_variants(self):
		from erpnext.stock.get_item_details import get_item_details

		if not frappe.db.exists("Item", "Test Variant PRT"):
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": "Test Variant PRT",
					"item_name": "Test Variant PRT",
					"description": "Test Variant PRT",
					"item_group": "_Test Item Group",
					"is_stock_item": 1,
					"variant_of": "_Test Variant Item",
					"default_warehouse": "_Test Warehouse - _TC",
					"stock_uom": "_Test UOM",
					"attributes": [{"attribute": "Test Size", "attribute_value": "Medium"}],
				}
			).insert()

		frappe.get_doc(
			{
				"doctype": "Pricing Rule",
				"title": "_Test Pricing Rule 1",
				"apply_on": "Item Code",
				"currency": "USD",
				"items": [
					{
						"item_code": "_Test Variant Item",
					}
				],
				"selling": 1,
				"rate_or_discount": "Discount Percentage",
				"rate": 0,
				"discount_percentage": 7.5,
				"company": "_Test Company",
			}
		).insert()

		args = frappe._dict(
			{
				"item_code": "Test Variant PRT",
				"company": "_Test Company",
				"price_list": "_Test Price List",
				"currency": "_Test Currency",
				"doctype": "Sales Order",
				"conversion_rate": 1,
				"price_list_currency": "_Test Currency",
				"plc_conversion_rate": 1,
				"order_type": "Sales",
				"customer": "_Test Customer",
				"name": None,
			}
		)

		details = get_item_details(args)
		self.assertEqual(details.get("discount_percentage"), 7.5)

		# add a new pricing rule for that item code, it should take priority
		frappe.get_doc(
			{
				"doctype": "Pricing Rule",
				"title": "_Test Pricing Rule 2",
				"apply_on": "Item Code",
				"items": [
					{
						"item_code": "Test Variant PRT",
					}
				],
				"currency": "USD",
				"selling": 1,
				"rate_or_discount": "Discount Percentage",
				"rate": 0,
				"discount_percentage": 17.5,
				"priority": 1,
				"company": "_Test Company",
			}
		).insert()

		details = get_item_details(args)
		self.assertEqual(details.get("discount_percentage"), 17.5)

	def test_pricing_rule_for_stock_qty(self):
		test_record = {
			"doctype": "Pricing Rule",
			"title": "_Test Pricing Rule",
			"apply_on": "Item Code",
			"currency": "USD",
			"items": [
				{
					"item_code": "_Test Item",
				}
			],
			"selling": 1,
			"rate_or_discount": "Discount Percentage",
			"rate": 0,
			"min_qty": 5,
			"max_qty": 7,
			"discount_percentage": 17.5,
			"company": "_Test Company",
		}
		frappe.get_doc(test_record.copy()).insert()

		if not frappe.db.get_value("UOM Conversion Detail", {"parent": "_Test Item", "uom": "box"}):
			item = frappe.get_doc("Item", "_Test Item")
			item.append("uoms", {"uom": "Box", "conversion_factor": 5})
			item.save(ignore_permissions=True)

		# With pricing rule
		so = make_sales_order(item_code="_Test Item", qty=1, uom="Box", do_not_submit=True)
		so.items[0].price_list_rate = 100
		so.submit()
		so = frappe.get_doc("Sales Order", so.name)
		self.assertEqual(so.items[0].discount_percentage, 17.5)
		self.assertEqual(so.items[0].rate, 82.5)

		# Without pricing rule
		so = make_sales_order(item_code="_Test Item", qty=2, uom="Box", do_not_submit=True)
		so.items[0].price_list_rate = 100
		so.submit()
		so = frappe.get_doc("Sales Order", so.name)
		self.assertEqual(so.items[0].discount_percentage, 0)
		self.assertEqual(so.items[0].rate, 100)

	def test_pricing_rule_with_margin_and_discount(self):
		frappe.delete_doc_if_exists("Pricing Rule", "_Test Pricing Rule")
		make_pricing_rule(
			selling=1, margin_type="Percentage", margin_rate_or_amount=10, discount_percentage=10
		)
		si = create_sales_invoice(do_not_save=True)
		si.items[0].price_list_rate = 1000
		si.payment_schedule = []
		si.insert(ignore_permissions=True)

		item = si.items[0]
		self.assertEqual(item.margin_rate_or_amount, 10)
		self.assertEqual(item.rate_with_margin, 1100)
		self.assertEqual(item.discount_percentage, 10)
		self.assertEqual(item.discount_amount, 110)
		self.assertEqual(item.rate, 990)

	def test_pricing_rule_with_margin_and_discount_amount(self):
		frappe.delete_doc_if_exists("Pricing Rule", "_Test Pricing Rule")
		make_pricing_rule(
			selling=1,
			margin_type="Percentage",
			margin_rate_or_amount=10,
			rate_or_discount="Discount Amount",
			discount_amount=110,
		)
		si = create_sales_invoice(do_not_save=True)
		si.items[0].price_list_rate = 1000
		si.payment_schedule = []
		si.insert(ignore_permissions=True)

		item = si.items[0]
		self.assertEqual(item.margin_rate_or_amount, 10)
		self.assertEqual(item.rate_with_margin, 1100)
		self.assertEqual(item.discount_amount, 110)
		self.assertEqual(item.rate, 990)

	def test_pricing_rule_for_product_discount_on_same_item(self):
		frappe.delete_doc_if_exists("Pricing Rule", "_Test Pricing Rule")
		test_record = {
			"doctype": "Pricing Rule",
			"title": "_Test Pricing Rule",
			"apply_on": "Item Code",
			"currency": "USD",
			"items": [
				{
					"item_code": "_Test Item",
				}
			],
			"selling": 1,
			"rate_or_discount": "Discount Percentage",
			"rate": 0,
			"min_qty": 0,
			"max_qty": 7,
			"discount_percentage": 17.5,
			"price_or_product_discount": "Product",
			"same_item": 1,
			"free_qty": 1,
			"company": "_Test Company",
		}
		frappe.get_doc(test_record.copy()).insert()

		# With pricing rule
		so = make_sales_order(item_code="_Test Item", qty=1)
		so.load_from_db()
		self.assertEqual(so.items[1].is_free_item, 1)
		self.assertEqual(so.items[1].item_code, "_Test Item")

	def test_pricing_rule_for_product_discount_on_different_item(self):
		frappe.delete_doc_if_exists("Pricing Rule", "_Test Pricing Rule")
		test_record = {
			"doctype": "Pricing Rule",
			"title": "_Test Pricing Rule",
			"apply_on": "Item Code",
			"currency": "USD",
			"items": [
				{
					"item_code": "_Test Item",
				}
			],
			"selling": 1,
			"rate_or_discount": "Discount Percentage",
			"rate": 0,
			"min_qty": 0,
			"max_qty": 7,
			"discount_percentage": 17.5,
			"price_or_product_discount": "Product",
			"same_item": 0,
			"free_item": "_Test Item 2",
			"free_qty": 1,
			"company": "_Test Company",
		}
		frappe.get_doc(test_record.copy()).insert()

		# With pricing rule
		so = make_sales_order(item_code="_Test Item", qty=1)
		so.load_from_db()
		self.assertEqual(so.items[1].is_free_item, 1)
		self.assertEqual(so.items[1].item_code, "_Test Item 2")

	def test_enforce_free_item_qty(self):
		# this test is only for testing non-enforcement as all other tests in this file already test with enforcement
		frappe.delete_doc_if_exists("Pricing Rule", "_Test Pricing Rule")
		test_record = {
			"doctype": "Pricing Rule",
			"title": "_Test Pricing Rule",
			"apply_on": "Item Code",
			"currency": "USD",
			"items": [
				{
					"item_code": "_Test Item",
				}
			],
			"selling": 1,
			"rate_or_discount": "Discount Percentage",
			"rate": 0,
			"min_qty": 0,
			"max_qty": 7,
			"discount_percentage": 17.5,
			"price_or_product_discount": "Product",
			"same_item": 0,
			"free_item": "_Test Item 2",
			"free_qty": 1,
			"company": "_Test Company",
		}
		pricing_rule = frappe.get_doc(test_record.copy()).insert()

		# With enforcement
		so = make_sales_order(item_code="_Test Item", qty=1, do_not_submit=True)
		self.assertEqual(so.items[1].is_free_item, 1)
		self.assertEqual(so.items[1].item_code, "_Test Item 2")

		# Test 1 : Saving a document with an item with pricing list without it's corresponding free item will cause it the free item to be refetched on save
		so.items.pop(1)
		so.save()
		so.reload()
		self.assertEqual(len(so.items), 2)

		# Without enforcement
		pricing_rule.enforce_free_item_qty = 0
		pricing_rule.save()

		# Test 2 : Deleted free item will not be fetched again on save without enfrocement
		so.items.pop(1)
		so.save()
		so.reload()
		self.assertEqual(len(so.items), 1)

	def test_dont_enforce_free_item_qty(self):
		# this test is only for testing non-enforcement as all other tests in this file already test with enforcement
		frappe.delete_doc_if_exists("Pricing Rule", "_Test Pricing Rule")
		test_record = {
			"doctype": "Pricing Rule",
			"title": "_Test Pricing Rule",
			"apply_on": "Item Code",
			"currency": "USD",
			"items": [
				{
					"item_code": "_Test Item",
				}
			],
			"selling": 1,
			"rate_or_discount": "Discount Percentage",
			"rate": 0,
			"min_qty": 0,
			"max_qty": 7,
			"discount_percentage": 17.5,
			"price_or_product_discount": "Product",
			"same_item": 0,
			"free_item": "_Test Item 2",
			"free_qty": 1,
			"company": "_Test Company",
		}
		pricing_rule = frappe.get_doc(test_record.copy()).insert()

		# With enforcement
		so = make_sales_order(item_code="_Test Item", qty=1, do_not_submit=True)
		self.assertEqual(so.items[1].is_free_item, 1)
		self.assertEqual(so.items[1].item_code, "_Test Item 2")

		# Test 1 : Saving a document with an item with pricing list without it's corresponding free item will cause it the free item to be refetched on save
		so.items.pop(1)
		so.save()
		so.reload()
		self.assertEqual(len(so.items), 2)

		# Without enforcement
		pricing_rule.dont_enforce_free_item_qty = 1
		pricing_rule.save()

		# Test 2 : Deleted free item will not be fetched again on save without enforcement
		so.items.pop(1)
		so.save()
		so.reload()
		self.assertEqual(len(so.items), 1)

	def test_cumulative_pricing_rule(self):
		frappe.delete_doc_if_exists("Pricing Rule", "_Test Cumulative Pricing Rule")
		test_record = {
			"doctype": "Pricing Rule",
			"title": "_Test Cumulative Pricing Rule",
			"apply_on": "Item Code",
			"currency": "USD",
			"items": [
				{
					"item_code": "_Test Item",
				}
			],
			"is_cumulative": 1,
			"selling": 1,
			"applicable_for": "Customer",
			"customer": "_Test Customer",
			"rate_or_discount": "Discount Percentage",
			"rate": 0,
			"min_amt": 0,
			"max_amt": 10000,
			"discount_percentage": 17.5,
			"price_or_product_discount": "Price",
			"company": "_Test Company",
			"valid_from": frappe.utils.nowdate(),
			"valid_upto": frappe.utils.nowdate(),
		}
		frappe.get_doc(test_record.copy()).insert()

		args = frappe._dict(
			{
				"item_code": "_Test Item",
				"company": "_Test Company",
				"price_list": "_Test Price List",
				"currency": "_Test Currency",
				"doctype": "Sales Invoice",
				"conversion_rate": 1,
				"price_list_currency": "_Test Currency",
				"plc_conversion_rate": 1,
				"order_type": "Sales",
				"customer": "_Test Customer",
				"name": None,
				"transaction_date": frappe.utils.nowdate(),
			}
		)
		details = get_item_details(args)

		self.assertTrue(details)

	def test_pricing_rule_for_condition(self):
		frappe.delete_doc_if_exists("Pricing Rule", "_Test Pricing Rule")

		make_pricing_rule(
			selling=1,
			margin_type="Percentage",
			condition="customer=='_Test Customer 1' and is_return==0",
			discount_percentage=10,
		)

		# Incorrect Customer and Correct is_return value
		si = create_sales_invoice(do_not_submit=True, customer="_Test Customer 2", is_return=0)
		si.items[0].price_list_rate = 1000
		si.submit()
		item = si.items[0]
		self.assertEqual(item.rate, 100)

		# Correct Customer and Incorrect is_return value
		si = create_sales_invoice(do_not_submit=True, customer="_Test Customer 1", is_return=1, qty=-1)
		si.items[0].price_list_rate = 1000
		si.submit()
		item = si.items[0]
		self.assertEqual(item.rate, 100)

		# Correct Customer and correct is_return value
		si = create_sales_invoice(do_not_submit=True, customer="_Test Customer 1", is_return=0)
		si.items[0].price_list_rate = 1000
		si.submit()
		item = si.items[0]
		self.assertEqual(item.rate, 900)

	def test_multiple_pricing_rules(self):
		make_pricing_rule(
			discount_percentage=20,
			selling=1,
			priority=1,
			apply_multiple_pricing_rules=1,
			title="_Test Pricing Rule 1",
		)
		make_pricing_rule(
			discount_percentage=10,
			selling=1,
			title="_Test Pricing Rule 2",
			priority=2,
			apply_multiple_pricing_rules=1,
		)
		si = create_sales_invoice(do_not_submit=True, customer="_Test Customer 1", qty=1)
		self.assertEqual(si.items[0].discount_percentage, 30)
		si.delete()

		frappe.delete_doc_if_exists("Pricing Rule", "_Test Pricing Rule 1")
		frappe.delete_doc_if_exists("Pricing Rule", "_Test Pricing Rule 2")

	def test_multiple_pricing_rules_with_apply_discount_on_discounted_rate(self):
		frappe.delete_doc_if_exists("Pricing Rule", "_Test Pricing Rule")

		make_pricing_rule(
			discount_percentage=20,
			selling=1,
			priority=1,
			apply_multiple_pricing_rules=1,
			title="_Test Pricing Rule 1",
		)
		make_pricing_rule(
			discount_percentage=10,
			selling=1,
			priority=2,
			apply_discount_on_rate=1,
			title="_Test Pricing Rule 2",
			apply_multiple_pricing_rules=1,
		)

		si = create_sales_invoice(do_not_submit=True, customer="_Test Customer 1", qty=1)
		self.assertEqual(si.items[0].discount_percentage, 28)
		si.delete()

		frappe.delete_doc_if_exists("Pricing Rule", "_Test Pricing Rule 1")
		frappe.delete_doc_if_exists("Pricing Rule", "_Test Pricing Rule 2")

	def test_item_price_with_pricing_rule(self):
		item = make_item("Water Flask")
		make_item_price("Water Flask", "_Test Price List", 100)

		pricing_rule_record = {
			"doctype": "Pricing Rule",
			"title": "_Test Water Flask Rule",
			"apply_on": "Item Code",
			"items": [
				{
					"item_code": "Water Flask",
				}
			],
			"selling": 1,
			"currency": "INR",
			"rate_or_discount": "Rate",
			"rate": 0,
			"margin_type": "Percentage",
			"margin_rate_or_amount": 2,
			"company": "_Test Company",
		}
		rule = frappe.get_doc(pricing_rule_record)
		rule.insert()

		si = create_sales_invoice(do_not_save=True, item_code="Water Flask")
		si.selling_price_list = "_Test Price List"
		si.save()

		# If rate in Rule is 0, give preference to Item Price if it exists
		self.assertEqual(si.items[0].price_list_rate, 100)
		self.assertEqual(si.items[0].margin_rate_or_amount, 2)
		self.assertEqual(si.items[0].rate_with_margin, 102)
		self.assertEqual(si.items[0].rate, 102)

		si.delete()
		rule.delete()
		frappe.get_doc("Item Price", {"item_code": "Water Flask"}).delete()
		item.delete()

	def test_item_price_with_blank_uom_pricing_rule(self):
		properties = {
			"item_code": "Item Blank UOM",
			"stock_uom": "Nos",
			"sales_uom": "Box",
			"uoms": [dict(uom="Box", conversion_factor=10)],
		}
		item = make_item(properties=properties)

		make_item_price("Item Blank UOM", "_Test Price List", 100)

		pricing_rule_record = {
			"doctype": "Pricing Rule",
			"title": "_Test Item Blank UOM Rule",
			"apply_on": "Item Code",
			"items": [
				{
					"item_code": "Item Blank UOM",
				}
			],
			"selling": 1,
			"currency": "INR",
			"rate_or_discount": "Rate",
			"rate": 101,
			"company": "_Test Company",
		}
		rule = frappe.get_doc(pricing_rule_record)
		rule.insert()

		si = create_sales_invoice(
			do_not_save=True, item_code="Item Blank UOM", uom="Box", conversion_factor=10
		)
		si.selling_price_list = "_Test Price List"
		si.save()

		# If UOM is blank consider it as stock UOM and apply pricing_rule on all UOM.
		# rate is 101, Selling UOM is Box that have conversion_factor of 10 so 101 * 10 = 1010
		self.assertEqual(si.items[0].price_list_rate, 1010)
		self.assertEqual(si.items[0].rate, 1010)

		si.delete()

		si = create_sales_invoice(do_not_save=True, item_code="Item Blank UOM", uom="Nos")
		si.selling_price_list = "_Test Price List"
		si.save()

		# UOM is blank so consider it as stock UOM and apply pricing_rule on all UOM.
		# rate is 101, Selling UOM is Nos that have conversion_factor of 1 so 101 * 1 = 101
		self.assertEqual(si.items[0].price_list_rate, 101)
		self.assertEqual(si.items[0].rate, 101)

		si.delete()
		rule.delete()
		frappe.get_doc("Item Price", {"item_code": "Item Blank UOM"}).delete()

		item.delete()

	def test_item_price_with_selling_uom_pricing_rule(self):
		properties = {
			"item_code": "Item UOM other than Stock",
			"stock_uom": "Nos",
			"sales_uom": "Box",
			"uoms": [dict(uom="Box", conversion_factor=10)],
		}
		item = make_item(properties=properties)

		make_item_price("Item UOM other than Stock", "_Test Price List", 100)

		pricing_rule_record = {
			"doctype": "Pricing Rule",
			"title": "_Test Item UOM other than Stock Rule",
			"apply_on": "Item Code",
			"items": [
				{
					"item_code": "Item UOM other than Stock",
					"uom": "Box",
				}
			],
			"selling": 1,
			"currency": "INR",
			"rate_or_discount": "Rate",
			"rate": 101,
			"company": "_Test Company",
		}
		rule = frappe.get_doc(pricing_rule_record)
		rule.insert()

		si = create_sales_invoice(
			do_not_save=True, item_code="Item UOM other than Stock", uom="Box", conversion_factor=10
		)
		si.selling_price_list = "_Test Price List"
		si.save()

		# UOM is Box so apply pricing_rule only on Box UOM.
		# Selling UOM is Box and as both UOM are same no need to multiply by conversion_factor.
		self.assertEqual(si.items[0].price_list_rate, 101)
		self.assertEqual(si.items[0].rate, 101)

		si.delete()

		si = create_sales_invoice(do_not_save=True, item_code="Item UOM other than Stock", uom="Nos")
		si.selling_price_list = "_Test Price List"
		si.save()

		# UOM is Box so pricing_rule won't apply as selling_uom is Nos.
		# As Pricing Rule is not applied price of 100 will be fetched from Item Price List.
		self.assertEqual(si.items[0].price_list_rate, 100)
		self.assertEqual(si.items[0].rate, 100)

		si.delete()
		rule.delete()
		frappe.get_doc("Item Price", {"item_code": "Item UOM other than Stock"}).delete()

		item.delete()

	def test_item_group_price_with_blank_uom_pricing_rule(self):
		group = frappe.get_doc(doctype="Item Group", item_group_name="_Test Pricing Rule Item Group")
		group.save()
		properties = {
			"item_code": "Item with Group Blank UOM",
			"item_group": "_Test Pricing Rule Item Group",
			"stock_uom": "Nos",
			"sales_uom": "Box",
			"uoms": [dict(uom="Box", conversion_factor=10)],
		}
		item = make_item(properties=properties)

		make_item_price("Item with Group Blank UOM", "_Test Price List", 100)

		pricing_rule_record = {
			"doctype": "Pricing Rule",
			"title": "_Test Item with Group Blank UOM Rule",
			"apply_on": "Item Group",
			"item_groups": [
				{
					"item_group": "_Test Pricing Rule Item Group",
				}
			],
			"selling": 1,
			"currency": "INR",
			"rate_or_discount": "Rate",
			"rate": 101,
			"company": "_Test Company",
		}
		rule = frappe.get_doc(pricing_rule_record)
		rule.insert()

		si = create_sales_invoice(
			do_not_save=True, item_code="Item with Group Blank UOM", uom="Box", conversion_factor=10
		)
		si.selling_price_list = "_Test Price List"
		si.save()

		# If UOM is blank consider it as stock UOM and apply pricing_rule on all UOM.
		# rate is 101, Selling UOM is Box that have conversion_factor of 10 so 101 * 10 = 1010
		self.assertEqual(si.items[0].price_list_rate, 1010)
		self.assertEqual(si.items[0].rate, 1010)

		si.delete()

		si = create_sales_invoice(do_not_save=True, item_code="Item with Group Blank UOM", uom="Nos")
		si.selling_price_list = "_Test Price List"
		si.save()

		# UOM is blank so consider it as stock UOM and apply pricing_rule on all UOM.
		# rate is 101, Selling UOM is Nos that have conversion_factor of 1 so 101 * 1 = 101
		self.assertEqual(si.items[0].price_list_rate, 101)
		self.assertEqual(si.items[0].rate, 101)

		si.delete()
		rule.delete()
		frappe.get_doc("Item Price", {"item_code": "Item with Group Blank UOM"}).delete()
		item.delete()
		group.delete()

	def test_item_group_price_with_selling_uom_pricing_rule(self):
		group = frappe.get_doc(doctype="Item Group", item_group_name="_Test Pricing Rule Item Group UOM")
		group.save()
		properties = {
			"item_code": "Item with Group UOM other than Stock",
			"item_group": "_Test Pricing Rule Item Group UOM",
			"stock_uom": "Nos",
			"sales_uom": "Box",
			"uoms": [dict(uom="Box", conversion_factor=10)],
		}
		item = make_item(properties=properties)

		make_item_price("Item with Group UOM other than Stock", "_Test Price List", 100)

		pricing_rule_record = {
			"doctype": "Pricing Rule",
			"title": "_Test Item with Group UOM other than Stock Rule",
			"apply_on": "Item Group",
			"item_groups": [
				{
					"item_group": "_Test Pricing Rule Item Group UOM",
					"uom": "Box",
				}
			],
			"selling": 1,
			"currency": "INR",
			"rate_or_discount": "Rate",
			"rate": 101,
			"company": "_Test Company",
		}
		rule = frappe.get_doc(pricing_rule_record)
		rule.insert()

		si = create_sales_invoice(
			do_not_save=True,
			item_code="Item with Group UOM other than Stock",
			uom="Box",
			conversion_factor=10,
		)
		si.selling_price_list = "_Test Price List"
		si.save()

		# UOM is Box so apply pricing_rule only on Box UOM.
		# Selling UOM is Box and as both UOM are same no need to multiply by conversion_factor.
		self.assertEqual(si.items[0].price_list_rate, 101)
		self.assertEqual(si.items[0].rate, 101)

		si.delete()

		si = create_sales_invoice(
			do_not_save=True, item_code="Item with Group UOM other than Stock", uom="Nos"
		)
		si.selling_price_list = "_Test Price List"
		si.save()

		# UOM is Box so pricing_rule won't apply as selling_uom is Nos.
		# As Pricing Rule is not applied price of 100 will be fetched from Item Price List.
		self.assertEqual(si.items[0].price_list_rate, 100)
		self.assertEqual(si.items[0].rate, 100)

		si.delete()
		rule.delete()
		frappe.get_doc("Item Price", {"item_code": "Item with Group UOM other than Stock"}).delete()
		item.delete()
		group.delete()

	def test_pricing_rule_for_different_currency(self):
		make_item("Test Sanitizer Item")

		pricing_rule_record = {
			"doctype": "Pricing Rule",
			"title": "_Test Sanitizer Rule",
			"apply_on": "Item Code",
			"items": [
				{
					"item_code": "Test Sanitizer Item",
				}
			],
			"selling": 1,
			"currency": "INR",
			"rate_or_discount": "Rate",
			"rate": 0,
			"priority": 2,
			"margin_type": "Percentage",
			"margin_rate_or_amount": 0.0,
			"company": "_Test Company",
		}

		rule = frappe.get_doc(pricing_rule_record)
		rule.rate_or_discount = "Rate"
		rule.rate = 100.0
		rule.insert()

		rule1 = frappe.get_doc(pricing_rule_record)
		rule1.currency = "USD"
		rule1.rate_or_discount = "Rate"
		rule1.rate = 2.0
		rule1.priority = 1
		rule1.insert()

		args = frappe._dict(
			{
				"item_code": "Test Sanitizer Item",
				"company": "_Test Company",
				"price_list": "_Test Price List",
				"currency": "USD",
				"doctype": "Sales Invoice",
				"conversion_rate": 1,
				"price_list_currency": "_Test Currency",
				"plc_conversion_rate": 1,
				"order_type": "Sales",
				"customer": "_Test Customer",
				"name": None,
				"transaction_date": frappe.utils.nowdate(),
			}
		)

		details = get_item_details(args)
		self.assertEqual(details.price_list_rate, 2.0)

		args = frappe._dict(
			{
				"item_code": "Test Sanitizer Item",
				"company": "_Test Company",
				"price_list": "_Test Price List",
				"currency": "INR",
				"doctype": "Sales Invoice",
				"conversion_rate": 1,
				"price_list_currency": "_Test Currency",
				"plc_conversion_rate": 1,
				"order_type": "Sales",
				"customer": "_Test Customer",
				"name": None,
				"transaction_date": frappe.utils.nowdate(),
			}
		)

		details = get_item_details(args)
		self.assertEqual(details.price_list_rate, 100.0)

	def test_pricing_rule_for_transaction(self):
		make_item("Water Flask 1")
		frappe.delete_doc_if_exists("Pricing Rule", "_Test Pricing Rule")
		make_pricing_rule(
			selling=1,
			min_qty=5,
			price_or_product_discount="Product",
			apply_on="Transaction",
			free_item="Water Flask 1",
			free_qty=1,
			free_item_rate=10,
		)

		si = create_sales_invoice(qty=5, do_not_submit=True)
		self.assertEqual(len(si.items), 2)
		self.assertEqual(si.items[1].rate, 10)

		si1 = create_sales_invoice(qty=2, do_not_submit=True)
		self.assertEqual(len(si1.items), 1)

		for doc in [si, si1]:
			doc.delete()

	def test_pricing_rule_for_transaction_with_condition(self):
		make_item("PR Transaction Condition")
		frappe.delete_doc_if_exists("Pricing Rule", "_Test Pricing Rule")
		make_pricing_rule(
			selling=1,
			min_qty=0,
			price_or_product_discount="Product",
			apply_on="Transaction",
			free_item="PR Transaction Condition",
			free_qty=1,
			free_item_rate=10,
			condition="customer=='_Test Customer 1'",
		)

		si = create_sales_invoice(qty=5, customer="_Test Customer 1", do_not_submit=True)
		self.assertEqual(len(si.items), 2)
		self.assertEqual(si.items[1].rate, 10)

		si1 = create_sales_invoice(qty=5, customer="_Test Customer 2", do_not_submit=True)
		self.assertEqual(len(si1.items), 1)

		for doc in [si, si1]:
			doc.delete()

	def test_remove_pricing_rule(self):
		item = make_item("Water Flask")
		make_item_price("Water Flask", "_Test Price List", 100)

		pricing_rule_record = {
			"doctype": "Pricing Rule",
			"title": "_Test Water Flask Rule",
			"apply_on": "Item Code",
			"price_or_product_discount": "Price",
			"items": [
				{
					"item_code": "Water Flask",
				}
			],
			"selling": 1,
			"currency": "INR",
			"rate_or_discount": "Discount Percentage",
			"discount_percentage": 20,
			"company": "_Test Company",
		}
		rule = frappe.get_doc(pricing_rule_record)
		rule.insert()

		si = create_sales_invoice(do_not_save=True, item_code="Water Flask")
		si.selling_price_list = "_Test Price List"
		si.save()

		self.assertEqual(si.items[0].price_list_rate, 100)
		self.assertEqual(si.items[0].discount_percentage, 20)
		self.assertEqual(si.items[0].rate, 80)

		si.ignore_pricing_rule = 1
		si.save()

		self.assertEqual(si.items[0].discount_percentage, 0)
		self.assertEqual(si.items[0].rate, 100)

		si.delete()
		rule.delete()
		frappe.get_doc("Item Price", {"item_code": "Water Flask"}).delete()
		item.delete()

	def test_multiple_pricing_rules_with_min_qty(self):
		make_pricing_rule(
			discount_percentage=20,
			selling=1,
			priority=1,
			min_qty=4,
			apply_multiple_pricing_rules=1,
			title="_Test Pricing Rule with Min Qty - 1",
		)
		make_pricing_rule(
			discount_percentage=10,
			selling=1,
			priority=2,
			min_qty=4,
			apply_multiple_pricing_rules=1,
			title="_Test Pricing Rule with Min Qty - 2",
		)

		si = create_sales_invoice(do_not_submit=True, customer="_Test Customer 1", qty=1)
		item = si.items[0]
		item.stock_qty = 1
		si.save()
		self.assertFalse(item.discount_percentage)
		item.qty = 5
		item.stock_qty = 5
		si.save()
		self.assertEqual(item.discount_percentage, 30)
		si.delete()

		frappe.delete_doc_if_exists("Pricing Rule", "_Test Pricing Rule with Min Qty - 1")
		frappe.delete_doc_if_exists("Pricing Rule", "_Test Pricing Rule with Min Qty - 2")

	def test_pricing_rule_for_other_items_cond_with_amount(self):
		item = make_item("Water Flask New")
		other_item = make_item("Other Water Flask New")
		make_item_price(item.name, "_Test Price List", 100)
		make_item_price(other_item.name, "_Test Price List", 100)

		pricing_rule_record = {
			"doctype": "Pricing Rule",
			"title": "_Test Water Flask Rule",
			"apply_on": "Item Code",
			"apply_rule_on_other": "Item Code",
			"price_or_product_discount": "Price",
			"rate_or_discount": "Discount Percentage",
			"other_item_code": other_item.name,
			"items": [
				{
					"item_code": item.name,
				}
			],
			"selling": 1,
			"currency": "INR",
			"min_amt": 200,
			"discount_percentage": 10,
			"company": "_Test Company",
		}
		rule = frappe.get_doc(pricing_rule_record)
		rule.insert()

		si = create_sales_invoice(do_not_save=True, item_code=item.name)
		si.append(
			"items",
			{
				"item_code": other_item.name,
				"item_name": other_item.item_name,
				"description": other_item.description,
				"stock_uom": other_item.stock_uom,
				"uom": other_item.stock_uom,
				"cost_center": si.items[0].cost_center,
				"expense_account": si.items[0].expense_account,
				"warehouse": si.items[0].warehouse,
				"conversion_factor": 1,
				"qty": 1,
			},
		)
		si.selling_price_list = "_Test Price List"
		si.save()

		self.assertEqual(si.items[0].discount_percentage, 0)
		self.assertEqual(si.items[1].discount_percentage, 0)

		si.items[0].qty = 2
		si.save()

		self.assertEqual(si.items[0].discount_percentage, 0)
		self.assertEqual(si.items[0].stock_qty, 2)
		self.assertEqual(si.items[0].amount, 200)
		self.assertEqual(si.items[0].price_list_rate, 100)
		self.assertEqual(si.items[1].discount_percentage, 10)

		si.delete()
		rule.delete()

	def test_pricing_rule_for_product_free_item_rounded_qty_and_recursion(self):
		frappe.delete_doc_if_exists("Pricing Rule", "_Test Pricing Rule")
		test_record = {
			"doctype": "Pricing Rule",
			"title": "_Test Pricing Rule",
			"apply_on": "Item Code",
			"currency": "USD",
			"items": [
				{
					"item_code": "_Test Item",
				}
			],
			"selling": 1,
			"rate": 0,
			"min_qty": 3,
			"max_qty": 7,
			"price_or_product_discount": "Product",
			"same_item": 1,
			"free_qty": 1,
			"round_free_qty": 1,
			"is_recursive": 1,
			"recurse_for": 2,
			"company": "_Test Company",
		}
		frappe.get_doc(test_record.copy()).insert()

		# With pricing rule
		so = make_sales_order(item_code="_Test Item", qty=5)
		so.load_from_db()
		self.assertEqual(so.items[1].is_free_item, 1)
		self.assertEqual(so.items[1].item_code, "_Test Item")
		self.assertEqual(so.items[1].qty, 2)

		so = make_sales_order(item_code="_Test Item", qty=7)
		so.load_from_db()
		self.assertEqual(so.items[1].is_free_item, 1)
		self.assertEqual(so.items[1].item_code, "_Test Item")
		self.assertEqual(so.items[1].qty, 3)

		so = make_sales_order(item_code="_Test Item", qty=5, do_not_submit=1)
		so.items[0].qty = 1
		del so.items[-1]
		so.set_missing_values()
		so.save()
		self.assertEqual(len(so.items), 1)

	def test_pricing_rules_with_min_qty_for_si_TC_ACC_103(self):
		make_pricing_rule(
			discount_percentage=10,
			selling=1,
			priority=2,
			min_qty=4,
			title="_Test Pricing Rule with Min Qty - 2",
		)

		si = create_sales_invoice(do_not_submit=True, customer="_Test Customer 1", qty=1)
		item = si.items[0]
		item.stock_qty = 1
		si.save()
		self.assertFalse(item.discount_percentage)
		item.qty = 5
		item.stock_qty = 5
		si.save()
		self.assertEqual(item.discount_percentage, 10)
		si.delete()

		frappe.delete_doc_if_exists("Pricing Rule", "_Test Pricing Rule with Min Qty - 1")
		frappe.delete_doc_if_exists("Pricing Rule", "_Test Pricing Rule with Min Qty - 2")

	def test_pricing_rules_with_min_qty_for_pi_TC_ACC_104(self):
		make_pricing_rule(
			discount_percentage=10,
			buying=1,
			priority=1,
			min_qty=4,
			title="_Test Pricing Rule",
		)

		pi = make_purchase_invoice(do_not_submit=True, supplier="_Test Supplier 1", qty=1)
		item = pi.items[0]
		item.stock_qty = 1
		pi.save()
		self.assertFalse(item.discount_percentage)
		item.qty = 5
		item.stock_qty = 5
		pi.save()
		self.assertEqual(item.discount_percentage, 10)
		pi.delete()

		frappe.delete_doc_if_exists("Pricing Rule", "_Test Pricing Rule with Min Qty - 1")
		frappe.delete_doc_if_exists("Pricing Rule", "_Test Pricing Rule with Min Qty - 2")

	def test_pricing_rule_for_product_free_item_round_free_qty(self):
		frappe.delete_doc_if_exists("Pricing Rule", "_Test Pricing Rule")
		test_record = {
			"doctype": "Pricing Rule",
			"title": "_Test Pricing Rule",
			"apply_on": "Item Code",
			"currency": "USD",
			"items": [
				{
					"item_code": "_Test Item",
				}
			],
			"selling": 1,
			"rate": 0,
			"min_qty": 100,
			"max_qty": 0,
			"price_or_product_discount": "Product",
			"same_item": 1,
			"free_qty": 10,
			"round_free_qty": 1,
			"is_recursive": 1,
			"recurse_for": 100,
			"company": "_Test Company",
		}
		frappe.get_doc(test_record.copy()).insert()
		# With pricing rule
		so = make_sales_order(item_code="_Test Item", qty=100)
		so.load_from_db()
		self.assertEqual(so.items[1].is_free_item, 1)
		self.assertEqual(so.items[1].item_code, "_Test Item")
		self.assertEqual(so.items[1].qty, 10)
		so = make_sales_order(item_code="_Test Item", qty=150)
		so.load_from_db()
		self.assertEqual(so.items[1].is_free_item, 1)
		self.assertEqual(so.items[1].item_code, "_Test Item")
		self.assertEqual(so.items[1].qty, 10)

	def test_apply_multiple_pricing_rules_for_discount_percentage_and_amount(self):
		frappe.delete_doc_if_exists("Pricing Rule", "_Test Pricing Rule 1")
		frappe.delete_doc_if_exists("Pricing Rule", "_Test Pricing Rule 2")
		test_record = {
			"doctype": "Pricing Rule",
			"title": "_Test Pricing Rule 1",
			"name": "_Test Pricing Rule 1",
			"apply_on": "Item Code",
			"currency": "USD",
			"items": [
				{
					"item_code": "_Test Item",
				}
			],
			"selling": 1,
			"price_or_product_discount": "Price",
			"rate_or_discount": "Discount Percentage",
			"discount_percentage": 10,
			"apply_multiple_pricing_rules": 1,
			"company": "_Test Company",
		}

		frappe.get_doc(test_record.copy()).insert()

		test_record = {
			"doctype": "Pricing Rule",
			"title": "_Test Pricing Rule 2",
			"name": "_Test Pricing Rule 2",
			"apply_on": "Item Code",
			"currency": "USD",
			"items": [
				{
					"item_code": "_Test Item",
				}
			],
			"selling": 1,
			"price_or_product_discount": "Price",
			"rate_or_discount": "Discount Amount",
			"discount_amount": 100,
			"apply_multiple_pricing_rules": 1,
			"company": "_Test Company",
		}

		frappe.get_doc(test_record.copy()).insert()

		so = make_sales_order(item_code="_Test Item", qty=1, price_list_rate=1000, do_not_submit=True)
		self.assertEqual(so.items[0].discount_amount, 200)
		self.assertEqual(so.items[0].rate, 800)

		frappe.delete_doc_if_exists("Sales Order", so.name)
		frappe.delete_doc_if_exists("Pricing Rule", "_Test Pricing Rule 1")
		frappe.delete_doc_if_exists("Pricing Rule", "_Test Pricing Rule 2")

	def test_priority_of_multiple_pricing_rules(self):
		frappe.delete_doc_if_exists("Pricing Rule", "_Test Pricing Rule 1")
		frappe.delete_doc_if_exists("Pricing Rule", "_Test Pricing Rule 2")

		test_record = {
			"doctype": "Pricing Rule",
			"title": "_Test Pricing Rule 1",
			"name": "_Test Pricing Rule 1",
			"apply_on": "Item Code",
			"currency": "USD",
			"items": [
				{
					"item_code": "_Test Item",
				}
			],
			"selling": 1,
			"price_or_product_discount": "Price",
			"rate_or_discount": "Discount Percentage",
			"discount_percentage": 10,
			"has_priority": 1,
			"priority": 1,
			"company": "_Test Company",
		}

		frappe.get_doc(test_record.copy()).insert()

		test_record = {
			"doctype": "Pricing Rule",
			"title": "_Test Pricing Rule 2",
			"name": "_Test Pricing Rule 2",
			"apply_on": "Item Code",
			"currency": "USD",
			"items": [
				{
					"item_code": "_Test Item",
				}
			],
			"selling": 1,
			"price_or_product_discount": "Price",
			"rate_or_discount": "Discount Percentage",
			"discount_percentage": 20,
			"has_priority": 1,
			"priority": 3,
			"company": "_Test Company",
		}

		frappe.get_doc(test_record.copy()).insert()

		so = make_sales_order(item_code="_Test Item", qty=1, price_list_rate=1000, do_not_submit=True)
		self.assertEqual(so.items[0].discount_percentage, 20)
		self.assertEqual(so.items[0].rate, 800)

		frappe.delete_doc_if_exists("Sales Order", so.name)
		frappe.delete_doc_if_exists("Pricing Rule", "_Test Pricing Rule 1")
		frappe.delete_doc_if_exists("Pricing Rule", "_Test Pricing Rule 2")

	def test_pricing_rules_with_and_without_apply_multiple(self):
		item = make_item("PR Item 99")

		test_records = [
			{
				"doctype": "Pricing Rule",
				"title": "_Test discount on item group",
				"name": "_Test discount on item group",
				"apply_on": "Item Group",
				"item_groups": [
					{
						"item_group": "Products",
					}
				],
				"selling": 1,
				"price_or_product_discount": "Price",
				"rate_or_discount": "Discount Percentage",
				"discount_percentage": 60,
				"has_priority": 1,
				"company": "_Test Company",
				"apply_multiple_pricing_rules": True,
			},
			{
				"doctype": "Pricing Rule",
				"title": "_Test fixed rate on item code",
				"name": "_Test fixed rate on item code",
				"apply_on": "Item Code",
				"items": [
					{
						"item_code": item.name,
					}
				],
				"selling": 1,
				"price_or_product_discount": "Price",
				"rate_or_discount": "Rate",
				"rate": 25,
				"has_priority": 1,
				"company": "_Test Company",
				"apply_multiple_pricing_rules": False,
			},
		]

		for item_group_priority, item_code_priority in [(2, 4), (4, 2)]:
			item_group_rule = frappe.get_doc(test_records[0].copy())
			item_group_rule.priority = item_group_priority
			item_group_rule.insert()

			item_code_rule = frappe.get_doc(test_records[1].copy())
			item_code_rule.priority = item_code_priority
			item_code_rule.insert()

			si = create_sales_invoice(qty=5, customer="_Test Customer 1", item=item.name, do_not_submit=True)
			si.save()
			self.assertEqual(len(si.pricing_rules), 1)
			# Item Code rule should've applied as it has higher priority
			expected_rule = item_group_rule if item_group_priority > item_code_priority else item_code_rule
			self.assertEqual(si.pricing_rules[0].pricing_rule, expected_rule.name)

			si.delete()
			item_group_rule.delete()
			item_code_rule.delete()

	def test_validation_on_mixed_condition_with_recursion(self):
		pricing_rule = make_pricing_rule(
			discount_percentage=10,
			selling=1,
			priority=2,
			min_qty=4,
			title="_Test Pricing Rule with Min Qty - 2",
		)
		pricing_rule.mixed_conditions = True
		pricing_rule.is_recursive = True
		self.assertRaises(frappe.ValidationError, pricing_rule.save)

	def test_ignore_pricing_rule_for_credit_note(self):
		frappe.delete_doc_if_exists("Pricing Rule", "_Test Pricing Rule")
		pricing_rule = make_pricing_rule(
			discount_percentage=20,
			selling=1,
			buying=1,
			priority=1,
			title="_Test Pricing Rule",
		)

		si = create_sales_invoice(do_not_submit=True, customer="_Test Customer 1", qty=1)
		item = si.items[0]
		si.submit()
		self.assertEqual(item.discount_percentage, 20)
		self.assertEqual(item.rate, 80)

		# change discount on pricing rule
		pricing_rule.discount_percentage = 30
		pricing_rule.save()

		credit_note = make_return_doc(si.doctype, si.name)
		credit_note.save()
		self.assertEqual(credit_note.ignore_pricing_rule, 1)
		self.assertEqual(credit_note.pricing_rules, [])
		self.assertEqual(credit_note.items[0].discount_percentage, 20)
		self.assertEqual(credit_note.items[0].rate, 80)
		self.assertEqual(credit_note.items[0].pricing_rules, None)

		credit_note.delete()
		si.cancel()

	def test_ignore_pricing_rule_for_debit_note(self):
		frappe.delete_doc_if_exists("Pricing Rule", "_Test Pricing Rule")
		pricing_rule = make_pricing_rule(
			discount_percentage=20,
			buying=1,
			priority=1,
			title="_Test Pricing Rule",
		)

		pi = make_purchase_invoice(do_not_submit=True, supplier="_Test Supplier 1", qty=1)
		item = pi.items[0]
		pi.submit()
		self.assertEqual(item.discount_percentage, 20)
		self.assertEqual(item.rate, 40)

		# change discount on pricing rule
		pricing_rule.discount_percentage = 30
		pricing_rule.save()

		# create debit note from purchase invoice
		debit_note = make_return_doc(pi.doctype, pi.name)
		debit_note.save()

		self.assertEqual(debit_note.ignore_pricing_rule, 1)
		self.assertEqual(debit_note.pricing_rules, [])
		self.assertEqual(debit_note.items[0].discount_percentage, 20)
		self.assertEqual(debit_note.items[0].rate, 40)
		self.assertEqual(debit_note.items[0].pricing_rules, None)

		debit_note.delete()
		pi.cancel()

	def test_pr_to_so_with_applied_on_transaction_TC_S_142(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item

		frappe.set_user("Administrator")
		item = make_test_item("_Test Item")
		item.save()

		item1 = make_test_item("_Test Item 1")
		item1.save()

		make_stock_entry(item_code="_Test Item 1", qty=5, rate=500, target="Stores - _TC")
		make_stock_entry(item_code="_Test Item", qty=5, rate=500, target="Stores - _TC")
		frappe.delete_doc_if_exists("Pricing Rule", "_Test Pricing Rule")
		make_pricing_rule(
			selling=1,
			min_qty=0,
			price_or_product_discount="Product",
			apply_on="Transaction",
			free_item="_Test Item 1",
			free_qty=1,
			free_item_rate=10,
			condition="customer=='_Test Customer'",
		)
		so = make_sales_order(qty=5, warehouse="Stores - _TC", do_not_save=True)
		so.set_warehouse = "Stores - _TC"
		so.save()
		so.submit()
		self.assertEqual(len(so.items), 2)
		self.assertEqual(so.items[1].rate, 10)

	def test_pr_to_so_with_applied_on_item_code_TC_S_143(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order as make_so

		frappe.set_user("Administrator")
		item = make_test_item("_Test Item")
		item.save()

		item1 = make_test_item("_Test Item 1")
		item1.save()

		sle = make_stock_entry(item_code="_Test Item 1", qty=5, rate=500, target="_Test Warehouse - _TC")
		sle2 = make_stock_entry(item_code="_Test Item", qty=5, rate=500, target="_Test Warehouse - _TC")
		sle.save()
		sle2.save()
		frappe.delete_doc_if_exists("Pricing Rule", "_Test Pricing Rule")

		pricing_rule_doc = frappe.new_doc("Pricing Rule")
		pricing_rule_data = {
			"title": "Free",
			"apply_on": "Item Code",
			"price_or_product_discount": "Product",
			"selling": 1,
			"min_qty": 0,
			"max_qty": 5,
			"company": "_Test Company",
			"items": [{"item_code": "_Test Item", "uom": "_Test UOM"}],
			"free_item": "_Test Item 1",
			"free_qty": 1,
			"free_item_rate": 10,
		}

		pricing_rule_doc.update(pricing_rule_data)
		pricing_rule_doc.save()

		so = make_so(
			item_code="_Test Item",
			qty=5,
			warehouse="_Test Warehouse - _TC",
			customer="_Test Customer",
			company="_Test Company",
			do_not_save=True,
		)
		so.set_warehouse = "_Test Warehouse - _TC"
		so.save()
		so.submit()
		self.assertEqual(len(so.items), 2)
		self.assertEqual(so.items[1].rate, 10)

	def test_pr_to_so_with_applied_on_item_group_TC_S_144(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item

		frappe.set_user("Administrator")
		create_item_group("_Test Item Group")

		item = make_test_item("_Test Item")
		item.item_group = "_Test Item Group"
		item.save()

		item1 = make_test_item("_Test Item 1")
		item1.item_group = "_Test Item Group"
		item1.save()

		make_stock_entry(item_code="_Test Item 1", qty=5, rate=500, target="Stores - _TC")
		make_stock_entry(item_code="_Test Item", qty=5, rate=500, target="Stores - _TC")
		frappe.delete_doc_if_exists("Pricing Rule", "_Test Pricing Rule")
		pricing_rule = frappe.get_doc(
			{
				"doctype": "Pricing Rule",
				"title": "_Test Pricing Rule",
				"apply_on": "Item Group",
				"selling": 1,
				"warehouse": "Stores - _TC",
				"price_or_product_discount": "Product",
				"free_item": "_Test Item 1",
				"free_qty": 1,
				"free_item_rate": 10,
				"condition": "customer=='_Test Customer'",
				"company": "_Test Company",
				"item_groups": [{"item_group": "_Test Item Group"}],
			}
		)
		pricing_rule.insert(ignore_permissions=True)
		item_list = [
			{"item_code": item.name, "warehouse": "Stores - _TC", "qty": 1},
		]
		so = make_sales_order(qty=5, warehouse="Stores - _TC", do_not_save=True, item_list=item_list)
		so.set_warehouse = "Stores - _TC"
		so.save()
		so.submit()
		self.assertEqual(len(so.items), 2)
		self.assertEqual(so.items[1].rate, 10)

	def test_pr_to_so_with_applied_on_brand_TC_S_145(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item

		frappe.set_user("Administrator")
		create_brand("_Test Brand 1")
		create_brand("_Test Brand")

		item = make_test_item("_Test Item")
		item.brand = "_Test Brand"
		item.save()

		item1 = make_test_item("_Test Item 1")
		item1.brand = "_Test Brand 1"
		item1.save()

		make_stock_entry(item_code="_Test Item 1", qty=5, rate=500, target="Stores - _TC")
		make_stock_entry(item_code="_Test Item", qty=5, rate=500, target="Stores - _TC")
		pricing_rule = frappe.get_doc(
			{
				"doctype": "Pricing Rule",
				"title": "_Test Pricing Rule",
				"apply_on": "Brand",
				"selling": 1,
				"warehouse": "Stores - _TC",
				"price_or_product_discount": "Product",
				"free_item": "_Test Item 1",
				"free_qty": 1,
				"free_item_rate": 10,
				"condition": "customer=='_Test Customer'",
				"company": "_Test Company",
				"brands": [{"brand": "_Test Brand"}],
			}
		)
		pricing_rule.insert(ignore_permissions=True)
		item_list = [
			{"item_code": item.name, "warehouse": "Stores - _TC", "qty": 1},
		]

		so = make_sales_order(warehouse="Stores - _TC", do_not_save=True, item_list=item_list)
		so.set_warehouse = "Stores - _TC"
		so.save()
		so.submit()
		self.assertEqual(len(so.items), 2)
		self.assertEqual(so.items[1].rate, 10)

	def test_cc_with_promotional_link_pr_TC_S_146(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item

		make_test_item("_Test Item 1")
		make_stock_entry(item_code="_Test Item 1", qty=5, rate=500, target="Stores - _TC")
		make_stock_entry(item_code="_Test Item", qty=5, rate=500, target="Stores - _TC")
		frappe.delete_doc_if_exists("Pricing Rule", "_Test Pricing Rule")
		pr = make_pricing_rule(
			selling=1,
			min_qty=0,
			price_or_product_discount="Product",
			apply_on="Item Code",
			warehouse="Stores - _TC",
			items=[{"item_code": "_Test Item 1"}],
			free_item="_Test Item 1",
			free_qty=1,
			free_item_rate=10,
			condition="customer=='_Test Customer'",
			company="_Test Company",
		)
		pr.coupon_code_based = 1
		pr.save()

		frappe.delete_doc_if_exists("Coupon Code", "SAVE30")

		coupon_code = frappe.get_doc(
			{
				"doctype": "Coupon Code",
				"coupon_type": "Promotional",
				"coupon_name": "SAVE30",
				"coupon_code": "SAVE30",
				"pricing_rule": pr.name,
				"maximum_use": 1,
				"used": 0,
			}
		)
		coupon_code.insert()
		self.assertEqual(coupon_code.coupon_type, "Promotional")
		self.assertEqual(coupon_code.pricing_rule, pr.name)

	def test_cc_with_gift_card_link_pr_TC_S_147(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item

		make_test_item("_Test Item 1")
		make_stock_entry(item_code="_Test Item 1", qty=5, rate=500, target="Stores - _TC")
		make_stock_entry(item_code="_Test Item", qty=5, rate=500, target="Stores - _TC")
		frappe.delete_doc_if_exists("Pricing Rule", "_Test Pricing Rule")
		pr = make_pricing_rule(
			selling=1,
			min_qty=0,
			price_or_product_discount="Product",
			apply_on="Item Code",
			warehouse="Stores - _TC",
			items=[{"item_code": "_Test Item 1"}],
			free_item="_Test Item 1",
			free_qty=1,
			free_item_rate=10,
			condition="customer=='_Test Customer'",
			company="_Test Company",
		)
		pr.coupon_code_based = 1
		pr.save()

		frappe.delete_doc_if_exists("Coupon Code", "SAVE30")

		coupon_code = frappe.get_doc(
			{
				"doctype": "Coupon Code",
				"coupon_type": "Gift Card",
				"customer": "_Test Customer",
				"coupon_name": "SAVE30",
				"coupon_code": "SAVE30",
				"pricing_rule": pr.name,
				"maximum_use": 1,
				"used": 0,
			}
		)
		coupon_code.insert()
		self.assertEqual(coupon_code.coupon_type, "Gift Card")
		self.assertEqual(coupon_code.pricing_rule, pr.name)

	def test_make_pricing_rule_TC_ACC_281(self):
		from erpnext.selling.doctype.customer.test_customer import get_customer_dict

		from .pricing_rule import make_pricing_rule

		customer = frappe.get_doc(get_customer_dict("__Test Pricing Rule Customer")).insert(
			ignore_permissions=True
		)
		rule = make_pricing_rule(customer.doctype, customer.name)
		self.assertEqual(rule.selling, 1)
		self.assertEqual(rule.buying, 0)

	def test_get_item_uoms_TC_ACC_282(self):
		from erpnext.accounts.doctype.pricing_rule.pricing_rule import get_item_uoms

		item = make_test_item("__Test Pricing Rule Item 1")
		item.append("uoms", {"uom": "Box", "conversion_factor": 1})
		item.save()

		# Correct: pass item_group as value
		filters = {"value": item.item_group, "apply_on": "Item Group"}

		result = get_item_uoms("Item", "Box", "uom", 0, 10, filters)
		uoms = [r[0] for r in result]

		self.assertIn("Box", uoms)
		self.assertNotIn("Dozen", uoms)

	def test_remove_pricing_rules_TC_ACC_283(self):
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice

		from .pricing_rule import remove_pricing_rules

		item = make_test_item("__Test Prising Rule Item 2")
		pr = make_pricing_rule(
			selling=1,
			min_qty=0,
			price_or_product_discount="Price",
			apply_on="Item Code",
			items=[{"item_code": item.item_code}],
			rate_or_discount="Rate",
			rate=50,
			title="Test Pricing Rule" + frappe.generate_hash(length=5),
		)
		si = create_sales_invoice(item_code=item.item_code, do_not_save=True)
		si.items[0].pricing_rules = pr.name
		si.insert()

		remove_rule = remove_pricing_rules(
			[
				{
					"doctype": "Sales Invoice Item",
					"name": si.items[0].name,
					"item_code": item.item_code,
					"pricing_rules": pr.name,
					"parenttype": "Sales Invoice",
					"parent": si.name,
					"price_list_rate": 50,
				}
			]
		)
		if remove_rule:
			self.assertEqual(remove_rule[0].get("item_code"), item.item_code)
			self.assertEqual(remove_rule[0].get("pricing_rules"), "")
			self.assertEqual(remove_rule[0].get("parent"), si.name)
			self.assertEqual(remove_rule[0].get("margin_rate_or_amount"), 0.0)
			self.assertEqual(remove_rule[0].get("pricing_rule_removed"), True)

	def test_validate_condition_TC_ACC_284(self):
		item = make_test_item("__Test Prising Rule Item 2")
		with self.assertRaises(frappe.ValidationError) as cm:
			make_pricing_rule(
				selling=1,
				min_qty=0,
				price_or_product_discount="Price",
				apply_on="Item Code",
				items=[{"item_code": item.item_code}],
				rate_or_discount="Rate",
				rate=50,
				condition="status = 'Draft'",
				title="Test Pricing Rule" + frappe.generate_hash(length=5),
			)
		self.assertIn("Invalid condition expression", str(cm.exception))

	def test_apply_pricing_rule_TC_ACC_285(self):
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice

		from .pricing_rule import apply_pricing_rule

		item = make_test_item("__Test Prising Rule Item 3")
		pr = make_pricing_rule(
			selling=1,
			min_qty=0,
			price_or_product_discount="Price",
			apply_on="Item Code",
			items=[{"item_code": item.item_code}],
			rate_or_discount="Rate",
			rate=50,
			title="Test Pricing Rule" + frappe.generate_hash(length=5),
		)
		si = create_sales_invoice(item_code=item.item_code, do_not_save=True)
		si.insert()

		item_list = {
			"items": [
				{
					"doctype": "Sales Invoice Item",
					"name": si.items[0].name,
					"child_docname": si.items[0].name,
					"item_code": item.item_code,
					"item_group": item.item_group,
					"qty": si.items[0].qty,
					"stock_qty": 1,
					"uom": "Nos",
					"stock_uom": "Nos",
					"parenttype": "Sales Invoice",
					"parent": si.name,
					"pricing_rules": json.dumps([pr.name]),
					"is_free_item": 0,
					"price_list_rate": 50,
					"conversion_factor": 1,
					"margin_type": "",
					"margin_rate_or_amount": 0,
				}
			],
			"customer": si.customer,
			"customer_group": "_Test Customer Group",
			"territory": si.territory,
			"currency": "INR",
			"conversion_rate": 1,
			"price_list": "Standard Selling",
			"price_list_currency": "INR",
			"plc_conversion_rate": 1,
			"company": si.company,
			"transaction_date": si.posting_date,
			"sales_partner": si.sales_partner,
			"ignore_pricing_rule": 0,
			"doctype": "Sales Invoice",
			"name": si.name,
			"is_return": 0,
			"update_stock": 0,
			"is_internal_customer": 0,
		}
		rule = apply_pricing_rule(args=item_list)
		if rule:
			self.assertFalse(rule[0].get("has_margin"))
			self.assertEqual(rule[0].get("free_item_data"), [])
			self.assertEqual(rule[0].get("margin_rate_or_amount"), 0.0)
			self.assertIsNone(rule[0].get("margin_type"))

	def test_validate_dates_TC_ACC_286(self):
		item = make_test_item("__Test Prising Rule Item 4")
		pr = make_pricing_rule(
			selling=1,
			min_qty=0,
			price_or_product_discount="Price",
			apply_on="Item Code",
			items=[{"item_code": item.item_code}],
			rate_or_discount="Rate",
			rate=50,
			title="Test Pricing Rule" + frappe.generate_hash(length=5),
		)
		with self.assertRaises(frappe.ValidationError) as cm:
			pr.is_cumulative = 1
			pr.save()
		self.assertIn("Valid from and valid upto fields are mandatory for the cumulative", str(cm.exception))

	def test_validate_mandatory_TC_ACC_287(self):
		pr = make_pricing_rule(selling=1, has_priority=1)
		pr.priority = ""
		with self.assertRaises(frappe.ValidationError) as cm:
			pr.save()
		self.assertIn("Priority is mandatory", str(cm.exception))

	def test_validate_apply_rule_on_other_TC_ACC_288(self):
		pr = make_pricing_rule(selling=1)
		pr.apply_rule_on_other = "Item Code"
		pr.other_item_code = ""
		with self.assertRaises(frappe.ValidationError) as cm:
			pr.save()
		self.assertIn(
			"For the 'Apply Rule On Other' condition the field Item Code is mandatory", str(cm.exception)
		)

	def test_validate_price_or_product_discount_TC_ACC_289(self):
		pr = make_pricing_rule(selling=1)
		pr.price_or_product_discount = "Price"
		pr.rate_or_discount = ""
		with self.assertRaises(frappe.ValidationError) as cm:
			pr.save()
		self.assertIn("Rate or Discount is required for the price discount.", str(cm.exception))

	def test_validate_apply_discount_on_rate_TC_ACC_290(self):
		pr = make_pricing_rule(selling=1)
		pr.apply_discount_on_rate = 1
		pr.has_priority = ""
		pr.priority = ""
		with self.assertRaises(frappe.ValidationError) as cm:
			pr.save()
		self.assertIn(
			"As the field Apply Discount on Discounted Rate is enabled, the field Priority is mandatory.",
			str(cm.exception),
		)

		pr_1 = make_pricing_rule(selling=1)
		pr_1.apply_discount_on_rate = 1
		pr_1.has_priority = ""
		pr_1.priority = 1
		with self.assertRaises(frappe.ValidationError) as cm:
			pr_1.save()
		self.assertIn(
			"As the field Apply Discount on Discounted Rate is enabled, the value of the field Priority should be more than 1.",
			str(cm.exception),
		)

	def test_validate_applicable_for_selling_or_buying_TC_ACC_291(self):
		with self.assertRaises(frappe.ValidationError) as cm:
			make_pricing_rule()
		self.assertIn("Atleast one of the Selling or Buying must be selected", str(cm.exception))

		pr = make_pricing_rule(selling=1)
		pr.max_qty = 10
		pr.min_qty = 15
		with self.assertRaises(frappe.ValidationError) as cm:
			pr.save()
		self.assertIn("Min Qty can not be greater than Max Qty", str(cm.exception))

		pr_1 = make_pricing_rule(selling=1)
		pr_1.min_amt = 20
		pr_1.max_amt = 15
		with self.assertRaises(frappe.ValidationError) as cm:
			pr_1.save()
		self.assertIn("Min Amt can not be greater than Max Amt", str(cm.exception))

		pr_2 = make_pricing_rule(selling=1)
		pr_2.rate_or_discount = "Rate"
		pr_2.rate = -20
		with self.assertRaises(frappe.ValidationError) as cm:
			pr_2.save()
		self.assertIn("Rate can not be negative", str(cm.exception))

		pr_3 = make_pricing_rule(selling=1)
		pr_3.price_or_product_discount = "Product"
		pr_3.free_item = ""
		pr_3.mixed_conditions = 1
		with self.assertRaises(frappe.ValidationError) as cm:
			pr_3.save()
		self.assertIn("Free item code is not selected", str(cm.exception))


# test_dependencies = ["Campaign"]


def make_pricing_rule(**args):
	args = frappe._dict(args)

	doc = frappe.get_doc(
		{
			"doctype": "Pricing Rule",
			"title": args.title or "_Test Pricing Rule",
			"company": args.company or "_Test Company",
			"apply_on": args.apply_on or "Item Code",
			"applicable_for": args.applicable_for,
			"selling": args.selling or 0,
			"currency": "INR",
			"apply_discount_on_rate": args.apply_discount_on_rate or 0,
			"buying": args.buying or 0,
			"min_qty": args.min_qty or 0.0,
			"max_qty": args.max_qty or 0.0,
			"rate_or_discount": args.rate_or_discount or "Discount Percentage",
			"discount_percentage": args.discount_percentage or 0.0,
			"rate": args.rate or 0.0,
			"margin_rate_or_amount": args.margin_rate_or_amount or 0.0,
			"condition": args.condition or "",
			"priority": args.priority or 1,
			"discount_amount": args.discount_amount or 0.0,
			"apply_multiple_pricing_rules": args.apply_multiple_pricing_rules or 0,
			"has_priority": args.has_priority or 0,
			"enforce_free_item_qty": args.dont_enforce_free_item_qty or 0,
		}
	)

	for field in [
		"free_item",
		"free_qty",
		"free_item_rate",
		"priority",
		"margin_type",
		"price_or_product_discount",
	]:
		if args.get(field):
			doc.set(field, args.get(field))

	apply_on = doc.apply_on.replace(" ", "_").lower()
	child_table = {"Item Code": "items", "Item Group": "item_groups", "Brand": "brands"}

	if doc.apply_on != "Transaction":
		doc.append(child_table.get(doc.apply_on), {apply_on: args.get(apply_on) or "_Test Item"})

	doc.insert(ignore_permissions=True)
	if args.get(apply_on) and apply_on != "item_code":
		doc.db_set(apply_on, args.get(apply_on))

	applicable_for = doc.applicable_for.replace(" ", "_").lower()
	if args.get(applicable_for):
		doc.db_set(applicable_for, args.get(applicable_for))

	return doc


def setup_pricing_rule_data():
	if not frappe.db.exists("Campaign", "_Test Campaign"):
		frappe.get_doc(
			{"doctype": "Campaign", "campaign_name": "_Test Campaign", "name": "_Test Campaign"}
		).insert()


def delete_existing_pricing_rules():
	for doctype in [
		"Pricing Rule",
		"Pricing Rule Item Code",
		"Pricing Rule Item Group",
		"Pricing Rule Brand",
	]:
		frappe.db.sql(f"delete from `tab{doctype}`")


def make_item_price(item, price_list_name, item_price):
	frappe.get_doc(
		{
			"doctype": "Item Price",
			"price_list": price_list_name,
			"item_code": item,
			"price_list_rate": item_price,
		}
	).insert(ignore_permissions=True, ignore_mandatory=True)


def create_brand(brand_name):
	if not frappe.db.exists("Brand", brand_name):
		doc = frappe.new_doc("Brand")
		doc.brand = brand_name
		doc.insert(ignore_permissions=True)


def create_item_group(group_name, is_group=False, parent_item_group="All Item Groups"):
	if not frappe.db.exists("Item Group", group_name):
		doc = frappe.new_doc("Item Group")
		doc.item_group_name = group_name
		doc.is_group = is_group
		doc.parent_item_group = parent_item_group
		doc.insert(ignore_permissions=True)


def get_or_create_customer(**kwargs):
	if not frappe.db.exists("Customer", kwargs.get("customer_name")):
		doc = frappe.new_doc("Customer")
		doc.update(kwargs)
		return doc.insert().name
	else:
		return kwargs.get("customer_name")
