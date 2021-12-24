# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from __future__ import unicode_literals

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
			"items": [{
				"item_code": "_Test Item"
			}],
			"currency": "USD",
			"selling": 1,
			"rate_or_discount": "Discount Percentage",
			"rate": 0,
			"discount_percentage": 10,
			"company": "_Test Company"
		}
		frappe.get_doc(test_record.copy()).insert()

		args = frappe._dict({
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
			"name": None
		})
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
		prule.append('item_groups', {
			'item_group': "All Item Groups"
		})
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
		from frappe import MandatoryError

		from erpnext.stock.get_item_details import get_item_details

		test_record = {
			"doctype": "Pricing Rule",
			"title": "_Test Pricing Rule",
			"apply_on": "Item Code",
			"items": [{
				"item_code": "_Test FG Item 2",
			}],
			"selling": 1,
			"currency": "USD",
			"rate_or_discount": "Discount Percentage",
			"rate": 0,
			"margin_type": "Percentage",
			"margin_rate_or_amount": 10,
			"company": "_Test Company"
		}
		frappe.get_doc(test_record.copy()).insert()

		item_price = frappe.get_doc({
			"doctype": "Item Price",
			"price_list": "_Test Price List 2",
			"item_code": "_Test FG Item 2",
			"price_list_rate": 100
		})

		item_price.insert(ignore_permissions=True)

		args = frappe._dict({
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
			"name": None
		})
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
					"item_group": "Seed",
				},
			],
			"selling": 1,
			"mixed_conditions": 1,
			"currency": "USD",
			"rate_or_discount": "Discount Percentage",
			"discount_percentage": 10,
			"applicable_for": "Customer Group",
			"customer_group": "All Customer Groups",
			"company": "_Test Company"
		}
		frappe.get_doc(test_record.copy()).insert()

		args = frappe._dict({
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
			"name": None
		})
		details = get_item_details(args)
		self.assertEqual(details.get("discount_percentage"), 10)

	def test_pricing_rule_for_variants(self):
		from frappe import MandatoryError

		from erpnext.stock.get_item_details import get_item_details

		if not frappe.db.exists("Item", "Test Variant PRT"):
			frappe.get_doc({
				"doctype": "Item",
				"item_code": "Test Variant PRT",
				"item_name": "Test Variant PRT",
				"description": "Test Variant PRT",
				"item_group": "_Test Item Group",
				"is_stock_item": 1,
				"variant_of": "_Test Variant Item",
				"default_warehouse": "_Test Warehouse - _TC",
				"stock_uom": "_Test UOM",
				"attributes": [
					{
					  "attribute": "Test Size",
					  "attribute_value": "Medium"
					}
				],
			}).insert()

		frappe.get_doc({
			"doctype": "Pricing Rule",
			"title": "_Test Pricing Rule 1",
			"apply_on": "Item Code",
			"currency": "USD",
			"items": [{
				"item_code": "_Test Variant Item",
			}],
			"selling": 1,
			"rate_or_discount": "Discount Percentage",
			"rate": 0,
			"discount_percentage": 7.5,
			"company": "_Test Company"
		}).insert()

		args = frappe._dict({
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
			"name": None
		})

		details = get_item_details(args)
		self.assertEqual(details.get("discount_percentage"), 7.5)

		# add a new pricing rule for that item code, it should take priority
		frappe.get_doc({
			"doctype": "Pricing Rule",
			"title": "_Test Pricing Rule 2",
			"apply_on": "Item Code",
			"items": [{
				"item_code": "Test Variant PRT",
			}],
			"currency": "USD",
			"selling": 1,
			"rate_or_discount": "Discount Percentage",
			"rate": 0,
			"discount_percentage": 17.5,
			"priority": 1,
			"company": "_Test Company"
		}).insert()

		details = get_item_details(args)
		self.assertEqual(details.get("discount_percentage"), 17.5)

	def test_pricing_rule_for_stock_qty(self):
		test_record = {
			"doctype": "Pricing Rule",
			"title": "_Test Pricing Rule",
			"apply_on": "Item Code",
			"currency": "USD",
			"items": [{
				"item_code": "_Test Item",
			}],
			"selling": 1,
			"rate_or_discount": "Discount Percentage",
			"rate": 0,
			"min_qty": 5,
			"max_qty": 7,
			"discount_percentage": 17.5,
			"company": "_Test Company"
		}
		frappe.get_doc(test_record.copy()).insert()

		if not frappe.db.get_value('UOM Conversion Detail',
			{'parent': '_Test Item', 'uom': 'box'}):
			item = frappe.get_doc('Item', '_Test Item')
			item.append('uoms', {
				'uom': 'Box',
				'conversion_factor': 5
			})
			item.save(ignore_permissions=True)

		# With pricing rule
		so = make_sales_order(item_code="_Test Item", qty=1, uom="Box", do_not_submit=True)
		so.items[0].price_list_rate = 100
		so.submit()
		so = frappe.get_doc('Sales Order', so.name)
		self.assertEqual(so.items[0].discount_percentage, 17.5)
		self.assertEqual(so.items[0].rate, 82.5)

		# Without pricing rule
		so = make_sales_order(item_code="_Test Item", qty=2, uom="Box", do_not_submit=True)
		so.items[0].price_list_rate = 100
		so.submit()
		so = frappe.get_doc('Sales Order', so.name)
		self.assertEqual(so.items[0].discount_percentage, 0)
		self.assertEqual(so.items[0].rate, 100)

	def test_pricing_rule_with_margin_and_discount(self):
		frappe.delete_doc_if_exists('Pricing Rule', '_Test Pricing Rule')
		make_pricing_rule(selling=1, margin_type="Percentage", margin_rate_or_amount=10, discount_percentage=10)
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
		frappe.delete_doc_if_exists('Pricing Rule', '_Test Pricing Rule')
		make_pricing_rule(selling=1, margin_type="Percentage", margin_rate_or_amount=10,
			rate_or_discount="Discount Amount", discount_amount=110)
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
		frappe.delete_doc_if_exists('Pricing Rule', '_Test Pricing Rule')
		test_record = {
			"doctype": "Pricing Rule",
			"title": "_Test Pricing Rule",
			"apply_on": "Item Code",
			"currency": "USD",
			"items": [{
				"item_code": "_Test Item",
			}],
			"selling": 1,
			"rate_or_discount": "Discount Percentage",
			"rate": 0,
			"min_qty": 0,
			"max_qty": 7,
			"discount_percentage": 17.5,
			"price_or_product_discount": "Product",
			"same_item": 1,
			"free_qty": 1,
			"company": "_Test Company"
		}
		frappe.get_doc(test_record.copy()).insert()

		# With pricing rule
		so = make_sales_order(item_code="_Test Item", qty=1)
		so.load_from_db()
		self.assertEqual(so.items[1].is_free_item, 1)
		self.assertEqual(so.items[1].item_code, "_Test Item")


	def test_pricing_rule_for_product_discount_on_different_item(self):
		frappe.delete_doc_if_exists('Pricing Rule', '_Test Pricing Rule')
		test_record = {
			"doctype": "Pricing Rule",
			"title": "_Test Pricing Rule",
			"apply_on": "Item Code",
			"currency": "USD",
			"items": [{
				"item_code": "_Test Item",
			}],
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
			"company": "_Test Company"
		}
		frappe.get_doc(test_record.copy()).insert()

		# With pricing rule
		so = make_sales_order(item_code="_Test Item", qty=1)
		so.load_from_db()
		self.assertEqual(so.items[1].is_free_item, 1)
		self.assertEqual(so.items[1].item_code, "_Test Item 2")

	def test_cumulative_pricing_rule(self):
		frappe.delete_doc_if_exists('Pricing Rule', '_Test Cumulative Pricing Rule')
		test_record = {
			"doctype": "Pricing Rule",
			"title": "_Test Cumulative Pricing Rule",
			"apply_on": "Item Code",
			"currency": "USD",
			"items": [{
				"item_code": "_Test Item",
			}],
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
			"valid_upto": frappe.utils.nowdate()
		}
		frappe.get_doc(test_record.copy()).insert()

		args = frappe._dict({
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
			"transaction_date": frappe.utils.nowdate()
		})
		details = get_item_details(args)

		self.assertTrue(details)

	def test_pricing_rule_for_condition(self):
		frappe.delete_doc_if_exists("Pricing Rule", "_Test Pricing Rule")

		make_pricing_rule(selling=1, margin_type="Percentage", \
			condition="customer=='_Test Customer 1' and is_return==0", discount_percentage=10)

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
		make_pricing_rule(discount_percentage=20, selling=1, priority=1, apply_multiple_pricing_rules=1,
			title="_Test Pricing Rule 1")
		make_pricing_rule(discount_percentage=10, selling=1, title="_Test Pricing Rule 2", priority=2,
			apply_multiple_pricing_rules=1)
		si = create_sales_invoice(do_not_submit=True, customer="_Test Customer 1", qty=1)
		self.assertEqual(si.items[0].discount_percentage, 30)
		si.delete()

		frappe.delete_doc_if_exists("Pricing Rule", "_Test Pricing Rule 1")
		frappe.delete_doc_if_exists("Pricing Rule", "_Test Pricing Rule 2")

	def test_multiple_pricing_rules_with_apply_discount_on_discounted_rate(self):
		frappe.delete_doc_if_exists("Pricing Rule", "_Test Pricing Rule")

		make_pricing_rule(discount_percentage=20, selling=1, priority=1, apply_multiple_pricing_rules=1,
			title="_Test Pricing Rule 1")
		make_pricing_rule(discount_percentage=10, selling=1, priority=2,
			apply_discount_on_rate=1, title="_Test Pricing Rule 2", apply_multiple_pricing_rules=1)

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
			"items": [{
				"item_code": "Water Flask",
			}],
			"selling": 1,
			"currency": "INR",
			"rate_or_discount": "Rate",
			"rate": 0,
			"margin_type": "Percentage",
			"margin_rate_or_amount": 2,
			"company": "_Test Company"
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

	def test_pricing_rule_for_transaction(self):
		make_item("Water Flask 1")
		frappe.delete_doc_if_exists('Pricing Rule', '_Test Pricing Rule')
		make_pricing_rule(selling=1, min_qty=5, price_or_product_discount="Product",
			apply_on="Transaction", free_item="Water Flask 1", free_qty=1, free_item_rate=10)

		si = create_sales_invoice(qty=5, do_not_submit=True)
		self.assertEqual(len(si.items), 2)
		self.assertEqual(si.items[1].rate, 10)

		si1 = create_sales_invoice(qty=2, do_not_submit=True)
		self.assertEqual(len(si1.items), 1)

		for doc in [si, si1]:
			doc.delete()

test_dependencies = ["Campaign"]

def make_pricing_rule(**args):
	args = frappe._dict(args)

	doc = frappe.get_doc({
		"doctype": "Pricing Rule",
		"title": args.title or "_Test Pricing Rule",
		"company": args.company or "_Test Company",
		"apply_on": args.apply_on or "Item Code",
		"applicable_for": args.applicable_for,
		"selling": args.selling or 0,
		"currency": "USD",
		"apply_discount_on_rate": args.apply_discount_on_rate or 0,
		"buying": args.buying or 0,
		"min_qty": args.min_qty or 0.0,
		"max_qty": args.max_qty or 0.0,
		"rate_or_discount": args.rate_or_discount or "Discount Percentage",
		"discount_percentage": args.discount_percentage or 0.0,
		"rate": args.rate or 0.0,
		"margin_rate_or_amount": args.margin_rate_or_amount or 0.0,
		"condition": args.condition or '',
		"priority": 1,
		"discount_amount": args.discount_amount or 0.0,
		"apply_multiple_pricing_rules": args.apply_multiple_pricing_rules or 0
	})

	for field in ["free_item", "free_qty", "free_item_rate", "priority",
		"margin_type", "price_or_product_discount"]:
		if args.get(field):
			doc.set(field, args.get(field))

	apply_on = doc.apply_on.replace(' ', '_').lower()
	child_table = {'Item Code': 'items', 'Item Group': 'item_groups', 'Brand': 'brands'}

	if doc.apply_on != "Transaction":
		doc.append(child_table.get(doc.apply_on), {
			apply_on: args.get(apply_on) or "_Test Item"
		})

	doc.insert(ignore_permissions=True)
	if args.get(apply_on) and apply_on != "item_code":
		doc.db_set(apply_on, args.get(apply_on))

	applicable_for = doc.applicable_for.replace(' ', '_').lower()
	if args.get(applicable_for):
		doc.db_set(applicable_for, args.get(applicable_for))

def setup_pricing_rule_data():
	if not frappe.db.exists('Campaign', '_Test Campaign'):
		frappe.get_doc({
			'doctype': 'Campaign',
			'campaign_name': '_Test Campaign',
			'name': '_Test Campaign'
		}).insert()

def delete_existing_pricing_rules():
	for doctype in ["Pricing Rule", "Pricing Rule Item Code",
		"Pricing Rule Item Group", "Pricing Rule Brand"]:

		frappe.db.sql("delete from `tab{0}`".format(doctype))


def make_item_price(item, price_list_name, item_price):
	frappe.get_doc({
		'doctype': 'Item Price',
		'price_list': price_list_name,
		'item_code': item,
		'price_list_rate': item_price
	}).insert(ignore_permissions=True, ignore_mandatory=True)
