# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.doctype.shipping_rule.shipping_rule import (
	FromGreaterThanToError,
	ManyBlankToValuesError,
	OverlappingConditionError,
)
from erpnext.controllers.sales_and_purchase_return import make_return_doc
from erpnext.tests.utils import ERPNextTestSuite

SHIPPING_ACCOUNT = "_Test Account Shipping Charges - _TC"


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

	def test_return_reverses_shipping_charge(self):
		shipping_rule = create_shipping_rule("Selling", "_Test Shipping Rule For Return")
		si = create_sales_invoice(qty=5, rate=100, do_not_save=1)
		si.shipping_rule = shipping_rule.name
		si.insert()
		si.submit()
		self.assertEqual(get_shipping_amounts(si), [200])

		credit_note = make_return_doc("Sales Invoice", si.name)
		credit_note.save()

		self.assertEqual(get_shipping_amounts(credit_note), [-200])
		self.assertEqual(credit_note.grand_total, -si.grand_total)

	def test_open_ended_condition_applies_from_its_from_value(self):
		shipping_rule = frappe.get_doc(
			{
				"doctype": "Shipping Rule",
				"label": "_Test Shipping Rule Open Ended",
				"shipping_rule_type": "Selling",
				"company": "_Test Company",
				"account": SHIPPING_ACCOUNT,
				"cost_center": "_Test Cost Center - _TC",
				"calculate_based_on": "Net Total",
				"conditions": [
					{"from_value": 1000, "to_value": 0, "shipping_amount": 20},
					{"from_value": 0, "to_value": 999.99, "shipping_amount": 100},
				],
			}
		).insert()

		self.assertEqual([d.from_value for d in shipping_rule.conditions], [0, 1000])
		self.assertEqual(shipping_rule.get_shipping_amount_from_rules(500), 100)
		self.assertEqual(shipping_rule.get_shipping_amount_from_rules(1500), 20)

	def test_changed_or_cleared_rule_removes_old_shipping_row(self):
		rule_a = create_shipping_rule("Selling", "_Test Shipping Rule Change A")
		rule_b = create_fixed_shipping_rule("_Test Shipping Rule Change B", "_Test Cost Center 2 - _TC")
		si = create_sales_invoice(qty=5, rate=100, do_not_save=1)
		si.shipping_rule = rule_a.name
		si.insert()
		self.assertEqual(get_shipping_amounts(si), [200])

		si.shipping_rule = rule_b.name
		si.save()
		shipping_rows = si.get("taxes", {"account_head": SHIPPING_ACCOUNT})
		self.assertEqual(
			[(row.cost_center, row.tax_amount) for row in shipping_rows], [("_Test Cost Center 2 - _TC", 40)]
		)

		si.shipping_rule = ""
		si.save()
		self.assertEqual(get_shipping_amounts(si), [])

	def test_disabled_rule_is_not_applied_to_new_document(self):
		shipping_rule = create_shipping_rule("Selling", "_Test Shipping Rule Disabled")
		saved_si = create_sales_invoice(qty=5, rate=100, do_not_save=1)
		saved_si.shipping_rule = shipping_rule.name
		saved_si.insert()

		shipping_rule.disabled = 1
		shipping_rule.save()

		si = create_sales_invoice(qty=5, rate=100, do_not_save=1)
		si.shipping_rule = shipping_rule.name
		# totals of an unsaved document, as when it is mapped from an order, are still calculated
		si.calculate_taxes_and_totals()
		self.assertRaisesRegex(frappe.ValidationError, "is disabled", si.insert)

		# A document saved before the rule was disabled can still be saved
		saved_si.reload()
		saved_si.save()
		self.assertEqual(get_shipping_amounts(saved_si), [200])


def get_shipping_amounts(doc):
	return [row.tax_amount for row in doc.get("taxes", {"account_head": SHIPPING_ACCOUNT})]


def create_fixed_shipping_rule(label, cost_center):
	return frappe.get_doc(
		{
			"doctype": "Shipping Rule",
			"label": label,
			"shipping_rule_type": "Selling",
			"company": "_Test Company",
			"account": SHIPPING_ACCOUNT,
			"cost_center": cost_center,
			"calculate_based_on": "Fixed",
			"shipping_amount": 40,
		}
	).insert()


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
