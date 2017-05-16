# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from __future__ import unicode_literals
import unittest
import frappe
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.stock.get_item_details import get_item_details
from frappe import MandatoryError

class TestPricingRule(unittest.TestCase):
	def test_pricing_rule_for_discount(self):
		from erpnext.stock.get_item_details import get_item_details
		from frappe import MandatoryError

		frappe.db.sql("delete from `tabPricing Rule`")

		test_record = {
			"doctype": "Pricing Rule",
			"title": "_Test Pricing Rule",
			"apply_on": "Item Code",
			"item_code": "_Test Item",
			"selling": 1,
			"price_or_discount": "Discount Percentage",
			"price": 0,
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
		self.assertEquals(details.get("discount_percentage"), 10)

		prule = frappe.get_doc(test_record.copy())
		prule.applicable_for = "Customer"
		prule.title = "_Test Pricing Rule for Customer"
		self.assertRaises(MandatoryError, prule.insert)

		prule.customer = "_Test Customer"
		prule.discount_percentage = 20
		prule.insert()
		details = get_item_details(args)
		self.assertEquals(details.get("discount_percentage"), 20)

		prule = frappe.get_doc(test_record.copy())
		prule.apply_on = "Item Group"
		prule.item_group = "All Item Groups"
		prule.title = "_Test Pricing Rule for Item Group"
		prule.discount_percentage = 15
		prule.insert()

		args.customer = "_Test Customer 1"
		details = get_item_details(args)
		self.assertEquals(details.get("discount_percentage"), 10)

		prule = frappe.get_doc(test_record.copy())
		prule.applicable_for = "Campaign"
		prule.campaign = "_Test Campaign"
		prule.title = "_Test Pricing Rule for Campaign"
		prule.discount_percentage = 5
		prule.priority = 8
		prule.insert()

		args.campaign = "_Test Campaign"
		details = get_item_details(args)
		self.assertEquals(details.get("discount_percentage"), 5)

		frappe.db.sql("update `tabPricing Rule` set priority=NULL where campaign='_Test Campaign'")
		from erpnext.accounts.doctype.pricing_rule.pricing_rule	import MultiplePricingRuleConflict
		self.assertRaises(MultiplePricingRuleConflict, get_item_details, args)

		args.item_code = "_Test Item 2"
		details = get_item_details(args)
		self.assertEquals(details.get("discount_percentage"), 15)

		frappe.db.sql("delete from `tabPricing Rule`")

	def test_pricing_rule_for_margin(self):
		from erpnext.stock.get_item_details import get_item_details
		from frappe import MandatoryError

		frappe.db.sql("delete from `tabPricing Rule`")

		test_record = {
			"doctype": "Pricing Rule",
			"title": "_Test Pricing Rule",
			"apply_on": "Item Code",
			"item_code": "_Test FG Item 2",
			"selling": 1,
			"price_or_discount": "Discount Percentage",
			"price": 0,
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
		self.assertEquals(details.get("margin_type"), "Percentage")
		self.assertEquals(details.get("margin_rate_or_amount"), 10)

		frappe.db.sql("delete from `tabPricing Rule`")

	def test_pricing_rule_for_variants(self):
		from erpnext.stock.get_item_details import get_item_details
		from frappe import MandatoryError

		frappe.db.sql("delete from `tabPricing Rule`")

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
			"item_code": "_Test Variant Item",
			"selling": 1,
			"price_or_discount": "Discount Percentage",
			"price": 0,
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
		self.assertEquals(details.get("discount_percentage"), 7.5)

		# add a new pricing rule for that item code, it should take priority
		frappe.get_doc({
			"doctype": "Pricing Rule",
			"title": "_Test Pricing Rule 2",
			"apply_on": "Item Code",
			"item_code": "Test Variant PRT",
			"selling": 1,
			"price_or_discount": "Discount Percentage",
			"price": 0,
			"discount_percentage": 17.5,
			"company": "_Test Company"
		}).insert()

		details = get_item_details(args)
		self.assertEquals(details.get("discount_percentage"), 17.5)

	def test_pricing_rule_for_stock_qty(self):
		frappe.db.sql("delete from `tabPricing Rule`")

		test_record = {
			"doctype": "Pricing Rule",
			"title": "_Test Pricing Rule",
			"apply_on": "Item Code",
			"item_code": "_Test Item",
			"selling": 1,
			"price_or_discount": "Discount Percentage",
			"price": 0,
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
		self.assertEquals(so.items[0].discount_percentage, 17.5)
		self.assertEquals(so.items[0].rate, 82.5)

		# Without pricing rule
		so = make_sales_order(item_code="_Test Item", qty=2, uom="Box", do_not_submit=True)
		so.items[0].price_list_rate = 100
		so.submit()
		so = frappe.get_doc('Sales Order', so.name)
		self.assertEquals(so.items[0].discount_percentage, 0)
		self.assertEquals(so.items[0].rate, 100)