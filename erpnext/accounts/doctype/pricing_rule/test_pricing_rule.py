# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from __future__ import unicode_literals
import unittest
import frappe

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
			"parenttype": "Sales Order",
			"conversion_rate": 1,
			"price_list_currency": "_Test Currency",
			"plc_conversion_rate": 1,
			"order_type": "Sales",
			"transaction_type": "selling",
			"customer": "_Test Customer",
			"doctype": "Sales Order Item",
			"name": None
		})
		details = get_item_details(args)
		self.assertEquals(details.get("discount_percentage"), 10)

		prule = frappe.get_doc(test_record.copy())
		prule.applicable_for = "Customer"
		self.assertRaises(MandatoryError, prule.insert)
		prule.customer = "_Test Customer"
		prule.discount_percentage = 20
		prule.insert()
		details = get_item_details(args)
		self.assertEquals(details.get("discount_percentage"), 20)

		prule = frappe.get_doc(test_record.copy())
		prule.apply_on = "Item Group"
		prule.item_group = "All Item Groups"
		prule.discount_percentage = 15
		prule.insert()

		args.customer = None
		details = get_item_details(args)
		self.assertEquals(details.get("discount_percentage"), 10)

		prule = frappe.get_doc(test_record.copy())
		prule.applicable_for = "Campaign"
		prule.campaign = "_Test Campaign"
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
