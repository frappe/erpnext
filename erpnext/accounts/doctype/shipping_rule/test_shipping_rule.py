# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from erpnext.accounts.doctype.shipping_rule.shipping_rule import (
	FromGreaterThanToError,
	ManyBlankToValuesError,
	OverlappingConditionError,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestShippingRule(ERPNextTestSuite):
	def setUp(self):
		self.load_test_records("Shipping Rule")

	def test_account_company_on_insert(self):
		for rule_type in ("Selling", "Buying"):
			with self.subTest(shipping_rule_type=rule_type):
				shipping_rule = frappe.copy_doc(self.globalTestRecords["Shipping Rule"][0])
				shipping_rule.label = f"{rule_type} Delivery"
				shipping_rule.shipping_rule_type = rule_type
				shipping_rule.company = "_Test Company 1"
				shipping_rule.cost_center = None
				with self.assertRaisesRegex(frappe.ValidationError, "does not belong to Company"):
					shipping_rule.insert()

	def test_account_company_on_update(self):
		shipping_rule = create_shipping_rule("Selling", "Standard Delivery")
		shipping_rule.company = "_Test Company 1"
		shipping_rule.cost_center = None
		with self.assertRaisesRegex(frappe.ValidationError, "does not belong to Company"):
			shipping_rule.save()

		shipping_rule.reload()
		shipping_rule.company = "_Test Company 1"
		shipping_rule.account = "_Test Account Shipping Charges - _TC1"
		shipping_rule.cost_center = None
		shipping_rule.save()
		shipping_rule.reload()
		self.assertEqual(shipping_rule.company, "_Test Company 1")
		self.assertEqual(shipping_rule.account, "_Test Account Shipping Charges - _TC1")

		shipping_rule.account = "_Test Account Shipping Charges - _TC"
		with self.assertRaisesRegex(frappe.ValidationError, "does not belong to Company"):
			shipping_rule.save()

	def test_from_greater_than_to(self):
		shipping_rule = frappe.copy_doc(self.globalTestRecords["Shipping Rule"][0])
		shipping_rule.name = self.globalTestRecords["Shipping Rule"][0].get("name")
		shipping_rule.get("conditions")[0].from_value = 101
		self.assertRaises(FromGreaterThanToError, shipping_rule.insert)

	def test_many_zero_to_values(self):
		shipping_rule = frappe.copy_doc(self.globalTestRecords["Shipping Rule"][0])
		shipping_rule.name = self.globalTestRecords["Shipping Rule"][0].get("name")
		shipping_rule.get("conditions")[0].to_value = 0
		self.assertRaises(ManyBlankToValuesError, shipping_rule.insert)

	def test_overlapping_conditions(self):
		for range_a, range_b in [
			((50, 150), (0, 100)),
			((50, 150), (100, 200)),
			((50, 150), (75, 125)),
			((50, 150), (25, 175)),
			((50, 150), (50, 150)),
		]:
			shipping_rule = frappe.copy_doc(self.globalTestRecords["Shipping Rule"][0])
			shipping_rule.name = self.globalTestRecords["Shipping Rule"][0].get("name")
			shipping_rule.get("conditions")[0].from_value = range_a[0]
			shipping_rule.get("conditions")[0].to_value = range_a[1]
			shipping_rule.get("conditions")[1].from_value = range_b[0]
			shipping_rule.get("conditions")[1].to_value = range_b[1]
			self.assertRaises(OverlappingConditionError, shipping_rule.insert)


def create_shipping_rule(shipping_rule_type, shipping_rule_name):
	if frappe.db.exists("Shipping Rule", shipping_rule_name):
		return frappe.get_doc("Shipping Rule", shipping_rule_name)

	sr = frappe.new_doc("Shipping Rule")
	sr.account = "_Test Account Shipping Charges - _TC"
	sr.calculate_based_on = "Net Total"
	sr.company = "_Test Company"
	sr.cost_center = "_Test Cost Center - _TC"
	sr.label = shipping_rule_name
	sr.name = shipping_rule_name
	sr.shipping_rule_type = shipping_rule_type

	sr.append(
		"conditions",
		{
			"doctype": "Shipping Rule Condition",
			"from_value": 0,
			"parentfield": "conditions",
			"shipping_amount": 50.0,
			"to_value": 100,
		},
	)
	sr.append(
		"conditions",
		{
			"doctype": "Shipping Rule Condition",
			"from_value": 101,
			"parentfield": "conditions",
			"shipping_amount": 100.0,
			"to_value": 200,
		},
	)
	sr.append(
		"conditions",
		{
			"doctype": "Shipping Rule Condition",
			"from_value": 201,
			"parentfield": "conditions",
			"shipping_amount": 200.0,
			"to_value": 2000,
		},
	)
	sr.insert(ignore_permissions=True)

	return sr
