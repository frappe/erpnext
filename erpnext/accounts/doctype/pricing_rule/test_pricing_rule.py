# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import unittest

import frappe

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.get_item_details import get_item_details


class TestPricingRule(unittest.TestCase):
	def setUp(self):
		delete_existing_pricing_rules()
		setup_pricing_rule_data()

	def tearDown(self):
		delete_existing_pricing_rules()

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


test_dependencies = ["Campaign"]


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
