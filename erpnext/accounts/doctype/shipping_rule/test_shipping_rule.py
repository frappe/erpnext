# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import unittest

import frappe

from erpnext.accounts.doctype.shipping_rule.shipping_rule import (
	FromGreaterThanToError,
	ManyBlankToValuesError,
	OverlappingConditionError,
)

test_records = frappe.get_test_records("Shipping Rule")


class TestShippingRule(unittest.TestCase):
	def test_from_greater_than_to(self):
		shipping_rule = frappe.copy_doc(test_records[0])
		shipping_rule.name = test_records[0].get("name")
		shipping_rule.get("conditions")[0].from_value = 101
		self.assertRaises(FromGreaterThanToError, shipping_rule.insert)

	def test_many_zero_to_values(self):
		shipping_rule = frappe.copy_doc(test_records[0])
		shipping_rule.name = test_records[0].get("name")
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
			shipping_rule = frappe.copy_doc(test_records[0])
			shipping_rule.name = test_records[0].get("name")
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
	sr.submit()
	return sr
