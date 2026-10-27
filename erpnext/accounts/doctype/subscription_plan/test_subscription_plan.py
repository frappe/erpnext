# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.accounts.doctype.subscription_plan.subscription_plan import get_plan_rate

test_dependencies = ["Item"]


class TestSubscriptionPlan(FrappeTestCase):
	def test_plan_rate_needs_plan_read(self):
		from erpnext.tests.permission_test_utils import as_user, make_fenced_user

		plan = frappe.get_doc(
			{
				"doctype": "Subscription Plan",
				"plan_name": f"_Test Plan {frappe.generate_hash(length=6)}",
				"item": "_Test Item",
				"currency": "INR",
				"price_determination": "Fixed Rate",
				"cost": 100,
				"billing_interval": "Month",
				"billing_interval_count": 1,
			}
		).insert()

		with as_user(make_fenced_user("plan-rate-reader@example.com", ["Accounts User"])):
			self.assertEqual(get_plan_rate(plan.name), 100)

		with as_user(make_fenced_user("plan-rate-outsider@example.com", [])):
			self.assertRaises(frappe.PermissionError, get_plan_rate, plan.name)

	def test_price_list_discounts(self):
		price_list = frappe.get_doc(
			{
				"doctype": "Price List",
				"price_list_name": f"_Test Subscription Prices {frappe.generate_hash(length=6)}",
				"currency": "INR",
				"selling": 1,
			}
		).insert()
		frappe.get_doc(
			{
				"doctype": "Item Price",
				"item_code": "_Test Item",
				"price_list": price_list.name,
				"price_list_rate": 1000,
			}
		).insert()
		plan = frappe.get_doc(
			{
				"doctype": "Subscription Plan",
				"plan_name": f"_Test Plan {frappe.generate_hash(length=6)}",
				"item": "_Test Item",
				"currency": "INR",
				"price_determination": "Based On Price List",
				"price_list": price_list.name,
				"billing_interval": "Month",
				"billing_interval_count": 1,
			}
		).insert()
		for discounts, expected in (
			([], 1000),
			([{"discount_percentage": 10}], 900),
			([{"discount_amount": 100}], 900),
			([{"discount_amount": 100}, {"discount_percentage": 10}], 800),
			([{"discount_percentage": 10}, {"discount_amount": 100}], 800),
			(
				[
					{"discount_percentage": 20},
					{"discount_percentage": 10, "apply_discount_on_rate": 1},
					{"discount_amount": 100},
				],
				620,
			),
			([{"rate": 800}, {"discount_percentage": 10}, {"discount_amount": 100}], 620),
			(
				[
					{"discount_percentage": 10, "margin_type": "Percentage", "margin_rate_or_amount": 10},
					{"discount_amount": 100},
				],
				890,
			),
			(
				[
					{"rate": 800, "margin_type": "Percentage", "margin_rate_or_amount": 10},
					{"discount_amount": 100, "margin_type": "Amount", "margin_rate_or_amount": 50},
				],
				830,
			),
		):
			with self.subTest(discounts=discounts):
				rules = [
					frappe._dict(
						name=f"_Test Subscription Discount {index}",
						price_or_product_discount="Price",
						rate_or_discount="Rate"
						if "rate" in discount
						else "Discount Amount"
						if "discount_amount" in discount
						else "Discount Percentage",
						currency="INR",
						apply_multiple_pricing_rules=1,
						**discount,
					)
					for index, discount in enumerate(discounts)
				]
				with patch(
					"erpnext.accounts.doctype.pricing_rule.utils.get_pricing_rules", return_value=rules
				):
					self.assertAlmostEqual(get_plan_rate(plan.name, quantity=20), expected)
					self.assertAlmostEqual(
						get_plan_rate(plan.name, quantity=20, prorate_factor=0.5), expected / 2
					)
