# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.accounts.doctype.subscription_plan.subscription_plan import get_plan_rate


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
