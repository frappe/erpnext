# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.utils import add_days, nowdate

from erpnext.accounts.doctype.subscription.test_subscription import create_subscription
from erpnext.accounts.doctype.subscription_plan.subscription_plan import get_plan_rate
from erpnext.tests.utils import ERPNextTestSuite


class TestSubscriptionPlan(ERPNextTestSuite):
	"""Subscription Plan validates its interval and computes a rate. The Monthly
	Rate branch multiplies cost by the number of months in the billing window."""

	def setUp(self):
		frappe.set_user("Administrator")

	def make_plan(self, **args):
		args = frappe._dict(args)
		plan = frappe.new_doc("Subscription Plan")
		plan.plan_name = f"_Test Plan {frappe.generate_hash(length=6)}"
		plan.item = args.item or "_Test Item"
		plan.currency = args.currency or "INR"
		plan.price_determination = args.price_determination
		plan.cost = args.cost or 0
		plan.billing_interval = args.billing_interval or "Month"
		plan.billing_interval_count = (
			args.billing_interval_count if args.billing_interval_count is not None else 1
		)
		return plan

	def test_billing_interval_count_must_be_positive(self):
		plan = self.make_plan(price_determination="Fixed Rate", cost=100, billing_interval_count=0)
		self.assertRaises(frappe.ValidationError, plan.insert)

	def test_fixed_rate_applies_prorate_factor(self):
		plan = self.make_plan(price_determination="Fixed Rate", cost=100)
		plan.insert()
		self.assertEqual(get_plan_rate(plan.name), 100)
		self.assertEqual(get_plan_rate(plan.name, prorate_factor=0.5), 50)

	def test_plan_rate_needs_plan_read(self):
		from erpnext.tests.permission_test_utils import as_user, make_fenced_user

		plan = self.make_plan(price_determination="Fixed Rate", cost=100)
		plan.insert()

		with as_user(make_fenced_user("plan-rate-reader@example.com", ["Accounts User"])):
			self.assertEqual(get_plan_rate(plan.name), 100)

		with as_user(make_fenced_user("plan-rate-outsider@example.com", [])):
			self.assertRaises(frappe.PermissionError, get_plan_rate, plan.name)

	def test_monthly_rate_within_year(self):
		plan = self.make_plan(price_determination="Monthly Rate", cost=100)
		plan.insert()
		# Jan 1 - Mar 31 is 3 whole months; month-aligned so proration is 0
		rate = get_plan_rate(plan.name, start_date="2026-01-01", end_date="2026-03-31")
		self.assertEqual(rate, 300)

	def test_monthly_rate_across_year_boundary(self):
		# a 14-month span (Jan 2026 to Feb 2027) bills all 14 months, not just the
		# 2-month remainder that relativedelta.months alone would give
		plan = self.make_plan(price_determination="Monthly Rate", cost=100)
		plan.insert()
		rate = get_plan_rate(plan.name, start_date="2026-01-01", end_date="2027-02-28")
		self.assertEqual(rate, 1400)

	@ERPNextTestSuite.change_settings("Subscription Settings", {"prorate": 1})
	def test_monthly_rate_for_periods_not_starting_on_the_first(self):
		plan = self.make_plan(price_determination="Monthly Rate", cost=1000)
		plan.insert()
		for start_date, end_date, expected in (
			("2026-01-15", "2026-02-14", 1000),  # one whole month
			("2026-01-15", "2026-02-28", 1500),  # one month and 14 of the 28 days to 2026-03-15
			("2026-01-01", "2026-03-31", 3000),
		):
			with self.subTest(start_date=start_date, end_date=end_date):
				rate = get_plan_rate(plan.name, start_date=start_date, end_date=end_date)
				self.assertAlmostEqual(rate, expected)

	def make_price_list_plan(self):
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
		plan = self.make_plan(price_determination="Based On Price List")
		plan.price_list = price_list.name
		return plan.insert()

	def test_price_list_plan_needs_a_price_list(self):
		plan = self.make_plan(price_determination="Based On Price List")
		self.assertRaisesRegex(frappe.ValidationError, "Price List is required", plan.insert)

	def test_price_list_rate_uses_the_customer(self):
		plan = self.make_price_list_plan()
		with patch(
			"erpnext.utilities.product.get_pricing_rule_for_item",
			return_value=frappe._dict(price_list_rate=1000),
		) as get_pricing_rule:
			# Subscription passes the party positionally as `customer`
			for args, kwargs in (((1, "_Test Customer"), {}), ((), {"party": "_Test Customer"})):
				with self.subTest(args=args, kwargs=kwargs):
					self.assertEqual(get_plan_rate(plan.name, *args, **kwargs), 1000)
					self.assertEqual(get_pricing_rule.call_args.args[0].customer, "_Test Customer")

	def test_interval_change_refused_while_mixed_in_a_subscription(self):
		plan, other_plan, single_plan = (
			self.make_plan(price_determination="Fixed Rate", cost=100).insert() for _ in range(3)
		)
		start_date = add_days(nowdate(), 30)
		create_subscription(
			start_date=start_date,
			plans=[{"plan": plan.name, "qty": 1}, {"plan": other_plan.name, "qty": 1}],
		)
		create_subscription(start_date=start_date, plans=[{"plan": single_plan.name, "qty": 1}])

		for changes in ({"billing_interval": "Year"}, {"billing_interval_count": 2}):
			with self.subTest(changes=changes):
				plan.reload()
				plan.update(changes)
				self.assertRaisesRegex(frappe.ValidationError, "also use other plans", plan.save)

		# a plan that is alone in its subscription can still change
		single_plan.billing_interval = "Year"
		single_plan.save()

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
		plan = self.make_plan(price_determination="Based On Price List")
		plan.price_list = price_list.name
		plan.insert()
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
