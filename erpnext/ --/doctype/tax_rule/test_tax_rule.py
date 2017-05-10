# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from erpnext.accounts.doctype.tax_rule.tax_rule import IncorrectCustomerGroup, IncorrectSupplierType, ConflictingTaxRule, get_tax_template

test_records = frappe.get_test_records('Tax Rule')

class TestTaxRule(unittest.TestCase):
	def setUp(self):
		frappe.db.sql("delete from `tabTax Rule` where use_for_shopping_cart <> 1")

	def test_conflict(self):
		tax_rule1 = make_tax_rule(customer= "_Test Customer",
			sales_tax_template = "_Test Sales Taxes and Charges Template", priority = 1)
		tax_rule1.save()

		tax_rule2 = make_tax_rule(customer= "_Test Customer",
			sales_tax_template = "_Test Sales Taxes and Charges Template", priority = 1)

		self.assertRaises(ConflictingTaxRule, tax_rule2.save)

	def test_conflict_with_non_overlapping_dates(self):
		tax_rule1 = make_tax_rule(customer= "_Test Customer",
			sales_tax_template = "_Test Sales Taxes and Charges Template", priority = 1, from_date = "2015-01-01")
		tax_rule1.save()

		tax_rule2 = make_tax_rule(customer= "_Test Customer",
			sales_tax_template = "_Test Sales Taxes and Charges Template", priority = 1, to_date = "2013-01-01")

		tax_rule2.save()
		self.assertTrue(tax_rule2.name)

	def test_conflict_with_overlapping_dates(self):
		tax_rule1 = make_tax_rule(customer= "_Test Customer",
			sales_tax_template = "_Test Sales Taxes and Charges Template", priority = 1, from_date = "2015-01-01", to_date = "2015-01-05")
		tax_rule1.save()

		tax_rule2 = make_tax_rule(customer= "_Test Customer",
			sales_tax_template = "_Test Sales Taxes and Charges Template", priority = 1, from_date = "2015-01-03", to_date = "2015-01-09")

		self.assertRaises(ConflictingTaxRule, tax_rule2.save)

	def test_tax_template(self):
		tax_rule = make_tax_rule()
		self.assertEquals(tax_rule.purchase_tax_template, None)


	def test_select_tax_rule_based_on_customer(self):
		make_tax_rule(customer= "_Test Customer",
			sales_tax_template = "_Test Sales Taxes and Charges Template", save=1)

		make_tax_rule(customer= "_Test Customer 1",
			sales_tax_template = "_Test Sales Taxes and Charges Template 1", save=1)

		make_tax_rule(customer= "_Test Customer 2",
			sales_tax_template = "_Test Sales Taxes and Charges Template 2", save=1)

		self.assertEquals(get_tax_template("2015-01-01", {"customer":"_Test Customer 2"}),
			"_Test Sales Taxes and Charges Template 2")

	def test_select_tax_rule_based_on_better_match(self):
		make_tax_rule(customer= "_Test Customer", billing_city = "Test City", billing_state = "Test State",
			sales_tax_template = "_Test Sales Taxes and Charges Template", save=1)

		make_tax_rule(customer= "_Test Customer",  billing_city = "Test City1", billing_state = "Test State",
			sales_tax_template = "_Test Sales Taxes and Charges Template 1", save=1)

		self.assertEquals(get_tax_template("2015-01-01", {"customer":"_Test Customer", "billing_city": "Test City", "billing_state": "Test State"}),
			"_Test Sales Taxes and Charges Template")

	def test_select_tax_rule_based_on_state_match(self):
		make_tax_rule(customer= "_Test Customer", shipping_state = "Test State",
			sales_tax_template = "_Test Sales Taxes and Charges Template", save=1)

		make_tax_rule(customer= "_Test Customer", shipping_state = "Test State12",
			sales_tax_template = "_Test Sales Taxes and Charges Template 1", priority=2, save=1)

		self.assertEquals(get_tax_template("2015-01-01", {"customer":"_Test Customer", "shipping_state": "Test State"}),
			"_Test Sales Taxes and Charges Template")

	def test_select_tax_rule_based_on_better_priority(self):
		make_tax_rule(customer= "_Test Customer", billing_city = "Test City",
			sales_tax_template = "_Test Sales Taxes and Charges Template", priority=1, save=1)

		make_tax_rule(customer= "_Test Customer", billing_city = "Test City",
			sales_tax_template = "_Test Sales Taxes and Charges Template 1", priority=2, save=1)

		self.assertEquals(get_tax_template("2015-01-01", {"customer":"_Test Customer", "billing_city": "Test City"}),
			"_Test Sales Taxes and Charges Template 1")

	def test_select_tax_rule_based_cross_matching_keys(self):
		make_tax_rule(customer= "_Test Customer", billing_city = "Test City",
			sales_tax_template = "_Test Sales Taxes and Charges Template", save=1)

		make_tax_rule(customer= "_Test Customer 1", billing_city = "Test City 1",
			sales_tax_template = "_Test Sales Taxes and Charges Template 1", save=1)

		self.assertEquals(get_tax_template("2015-01-01", {"customer":"_Test Customer", "billing_city": "Test City 1"}),
			None)

	def test_select_tax_rule_based_cross_partially_keys(self):
		make_tax_rule(customer= "_Test Customer", billing_city = "Test City",
			sales_tax_template = "_Test Sales Taxes and Charges Template", save=1)

		make_tax_rule(billing_city = "Test City 1",
			sales_tax_template = "_Test Sales Taxes and Charges Template 1", save=1)

		self.assertEquals(get_tax_template("2015-01-01", {"customer":"_Test Customer", "billing_city": "Test City 1"}),
			"_Test Sales Taxes and Charges Template 1")


def make_tax_rule(**args):
	args = frappe._dict(args)

	tax_rule = frappe.new_doc("Tax Rule")

	for key, val in args.iteritems():
		if key != "save":
			tax_rule.set(key, val)

	tax_rule.company = args.company or "_Test Company"

	if args.save:
		tax_rule.insert()

	return tax_rule
