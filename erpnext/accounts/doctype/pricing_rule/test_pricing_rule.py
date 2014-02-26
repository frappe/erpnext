# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from __future__ import unicode_literals
import unittest
import frappe

class TestPricingRule(unittest.TestCase):
	def test_pricing_rule_for_discount(self):
		from erpnext.stock.get_item_details import get_item_details
		from frappe import MandatoryError
		
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
		
		prule = frappe.bean(copy=test_records[0])
		prule.doc.apply_on = "Item Group"
		prule.doc.item_group = "_Test Item Group"
		prule.doc.discount = 15
		prule.insert()
		
		details = get_item_details(args)
		self.assertEquals(details.get("discount_percentage"), 10)
		
		prule = frappe.bean(copy=test_records[0])
		prule.doc.applicable_for = "Customer"
		self.assertRaises(MandatoryError, prule.insert)
		prule.doc.customer = "_Test Customer"
		prule.doc.discount = 20
		prule.insert()
		details = get_item_details(args)
		self.assertEquals(details.get("discount_percentage"), 20)
		
		prule = frappe.bean(copy=test_records[0])
		prule.doc.applicable_for = "Campaign"
		prule.doc.campaign = "_Test Campaign"
		prule.doc.discount = 30
		prule.insert()
		args.campaign = "_Test Campaign"
		details = get_item_details(args)
		self.assertEquals(details.get("discount_percentage"), 30)
		
		args.item_code = "_Test Item 2"
		details = get_item_details(args)
		self.assertEquals(details.get("discount_percentage"), 15)
		
		args.customer = None
		details = get_item_details(args)
		self.assertEquals(details.get("discount_percentage"), 15)
		
		
		

test_records = [
	[{
		"doctype": "Pricing Rule", 
		"apply_on": "Item Code", 
		"item_code": "_Test Item", 
		"price_or_discount": "Discount", 
		"price": 0, 
		"discount": 10, 
	}],

]