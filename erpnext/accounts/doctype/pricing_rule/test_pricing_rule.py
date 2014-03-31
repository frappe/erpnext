# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from __future__ import unicode_literals
import unittest
import frappe

class TestPricingRule(unittest.TestCase):
	def test_pricing_rule_for_discount(self):
		from erpnext.stock.get_item_details import get_item_details
		from frappe import MandatoryError

		test_record = [{
			"doctype": "Pricing Rule", 
			"apply_on": "Item Code", 
			"item_code": "_Test Item", 
			"price_or_discount": "Discount Percentage", 
			"price": 0, 
			"discount_percentage": 10, 
		}]
		frappe.copy_doc(test_record).insert()
		
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
			"transaction_type": "selling",
			"customer": "_Test Customer",
		})
		
		details = get_item_details(args)
		self.assertEquals(details.get("discount_percentage"), 10)
		
		prule = frappe.copy_doc(test_record)
		prule.applicable_for = "Customer"
		self.assertRaises(MandatoryError, prule.insert)
		prule.customer = "_Test Customer"
		prule.discount_percentage = 20
		prule.insert()
		details = get_item_details(args)
		self.assertEquals(details.get("discount_percentage"), 20)
		
		prule = frappe.copy_doc(test_record)
		prule.apply_on = "Item Group"
		prule.item_group = "All Item Groups"
		prule.discount_percentage = 15
		prule.insert()
		
		args.customer = None
		details = get_item_details(args)
		self.assertEquals(details.get("discount_percentage"), 10)
		
		prule = frappe.copy_doc(test_record)
		prule.applicable_for = "Campaign"
		prule.campaign = "_Test Campaign"
		prule.discount_percentage = 5
		prule.priority = 8
		prule.insert()
		
		args.campaign = "_Test Campaign"
		details = get_item_details(args)
		self.assertEquals(details.get("discount_percentage"), 5)
		
		frappe.db.sql("update `tabPricing Rule` set priority=NULL where campaign='_Test Campaign'")
		details = get_item_details(args)
		self.assertEquals(details.get("discount_percentage"), 15)
		
		args.item_code = "_Test Item 2"
		details = get_item_details(args)
		self.assertEquals(details.get("discount_percentage"), 15)
		
		frappe.db.sql("delete from `tabPricing Rule`")