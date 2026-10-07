# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestAuthorizationRule(ERPNextTestSuite):
	def make_rule(self, **kwargs):
		return frappe.get_doc(
			{
				"doctype": "Authorization Rule",
				"transaction": "Sales Order",
				"based_on": "Grand Total",
				"approving_role": "Sales Manager",
				"value": 100000,
				**kwargs,
			}
		)

	def test_duplicate_rule_is_blocked(self):
		self.make_rule().insert(ignore_permissions=True)
		self.assertRaises(frappe.ValidationError, self.make_rule().insert, ignore_permissions=True)

	def test_rules_with_distinct_scope_or_limit_are_allowed(self):
		self.make_rule().insert(ignore_permissions=True)
		self.make_rule(value=50000).insert(ignore_permissions=True)
		self.make_rule(company="_Test Company").insert(ignore_permissions=True)

		for based_on, master_type, first, second in (
			("Customerwise Discount", "Customer", "_Test Customer", "_Test Customer 2"),
			("Itemwise Discount", "Item", "_Test Item", "_Test Item 2"),
		):
			with self.subTest(based_on=based_on):
				self.make_rule(
					based_on=based_on, value=10, customer_or_item=master_type, master_name=first
				).insert(ignore_permissions=True)
				self.make_rule(
					based_on=based_on, value=10, customer_or_item=master_type, master_name=second
				).insert(ignore_permissions=True)
