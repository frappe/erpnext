# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import unittest

import frappe
from frappe.tests import IntegrationTestCase

from erpnext.accounts.doctype.tax_rule.tax_rule import ConflictingTaxRule, get_tax_template
from erpnext.crm.doctype.opportunity.opportunity import make_quotation
from erpnext.crm.doctype.opportunity.test_opportunity import make_opportunity


class TestTaxRule(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.db.set_single_value("Shopping Cart Settings", "enabled", 0)

	@classmethod
	def tearDownClass(cls):
		frappe.db.sql("delete from `tabTax Rule`")

	def setUp(self):
		frappe.db.sql("delete from `tabTax Rule`")

	def test_conflict(self):
		tax_rule1 = make_tax_rule(
			customer="_Test Customer",
			sales_tax_template="_Test Sales Taxes and Charges Template - _TC",
			priority=1,
		)
		tax_rule1.save()

		tax_rule2 = make_tax_rule(
			customer="_Test Customer",
			sales_tax_template="_Test Sales Taxes and Charges Template - _TC",
			priority=1,
		)

		self.assertRaises(ConflictingTaxRule, tax_rule2.save)

	def test_conflict_with_non_overlapping_dates(self):
		tax_rule1 = make_tax_rule(
			customer="_Test Customer",
			sales_tax_template="_Test Sales Taxes and Charges Template - _TC",
			priority=1,
			from_date="2015-01-01",
		)
		tax_rule1.save()

		tax_rule2 = make_tax_rule(
			customer="_Test Customer",
			sales_tax_template="_Test Sales Taxes and Charges Template - _TC",
			priority=1,
			to_date="2013-01-01",
		)

		tax_rule2.save()
		self.assertTrue(tax_rule2.name)

	def test_for_parent_customer_group(self):
		tax_rule1 = make_tax_rule(
			customer_group="All Customer Groups",
			sales_tax_template="_Test Sales Taxes and Charges Template - _TC",
			priority=1,
			from_date="2015-01-01",
		)
		tax_rule1.save()
		self.assertEqual(
			get_tax_template("2015-01-01", {"customer_group": "Commercial", "use_for_shopping_cart": 1}),
			"_Test Sales Taxes and Charges Template - _TC",
		)

	def test_conflict_with_overlapping_dates(self):
		tax_rule1 = make_tax_rule(
			customer="_Test Customer",
			sales_tax_template="_Test Sales Taxes and Charges Template - _TC",
			priority=1,
			from_date="2015-01-01",
			to_date="2015-01-05",
		)
		tax_rule1.save()

		tax_rule2 = make_tax_rule(
			customer="_Test Customer",
			sales_tax_template="_Test Sales Taxes and Charges Template - _TC",
			priority=1,
			from_date="2015-01-03",
			to_date="2015-01-09",
		)

		self.assertRaises(ConflictingTaxRule, tax_rule2.save)

	def test_tax_template(self):
		tax_rule = make_tax_rule()
		self.assertEqual(tax_rule.purchase_tax_template, None)

	def test_select_tax_rule_based_on_customer(self):
		make_tax_rule(
			customer="_Test Customer",
			sales_tax_template="_Test Sales Taxes and Charges Template - _TC",
			save=1,
		)

		make_tax_rule(
			customer="_Test Customer 1",
			sales_tax_template="_Test Sales Taxes and Charges Template 1 - _TC",
			save=1,
		)

		make_tax_rule(
			customer="_Test Customer 2",
			sales_tax_template="_Test Sales Taxes and Charges Template 2 - _TC",
			save=1,
		)

		self.assertEqual(
			get_tax_template("2015-01-01", {"customer": "_Test Customer 2"}),
			"_Test Sales Taxes and Charges Template 2 - _TC",
		)

	def test_select_tax_rule_based_on_tax_category(self):
		make_tax_rule(
			customer="_Test Customer",
			tax_category="_Test Tax Category 1",
			sales_tax_template="_Test Sales Taxes and Charges Template 1 - _TC",
			save=1,
		)

		make_tax_rule(
			customer="_Test Customer",
			tax_category="_Test Tax Category 2",
			sales_tax_template="_Test Sales Taxes and Charges Template 2 - _TC",
			save=1,
		)

		self.assertFalse(get_tax_template("2015-01-01", {"customer": "_Test Customer"}))

		self.assertEqual(
			get_tax_template(
				"2015-01-01", {"customer": "_Test Customer", "tax_category": "_Test Tax Category 1"}
			),
			"_Test Sales Taxes and Charges Template 1 - _TC",
		)
		self.assertEqual(
			get_tax_template(
				"2015-01-01", {"customer": "_Test Customer", "tax_category": "_Test Tax Category 2"}
			),
			"_Test Sales Taxes and Charges Template 2 - _TC",
		)

		make_tax_rule(
			customer="_Test Customer",
			tax_category="",
			sales_tax_template="_Test Sales Taxes and Charges Template - _TC",
			save=1,
		)

		self.assertEqual(
			get_tax_template("2015-01-01", {"customer": "_Test Customer"}),
			"_Test Sales Taxes and Charges Template - _TC",
		)

	def test_select_tax_rule_based_on_better_match(self):
		make_tax_rule(
			customer="_Test Customer",
			billing_city="Test City",
			billing_state="Test State",
			sales_tax_template="_Test Sales Taxes and Charges Template - _TC",
			save=1,
		)

		make_tax_rule(
			customer="_Test Customer",
			billing_city="Test City1",
			billing_state="Test State",
			sales_tax_template="_Test Sales Taxes and Charges Template 1 - _TC",
			save=1,
		)

		self.assertEqual(
			get_tax_template(
				"2015-01-01",
				{"customer": "_Test Customer", "billing_city": "Test City", "billing_state": "Test State"},
			),
			"_Test Sales Taxes and Charges Template - _TC",
		)

	def test_select_tax_rule_based_on_state_match(self):
		make_tax_rule(
			customer="_Test Customer",
			shipping_state="Test State",
			sales_tax_template="_Test Sales Taxes and Charges Template - _TC",
			save=1,
		)

		make_tax_rule(
			customer="_Test Customer",
			shipping_state="Test State12",
			sales_tax_template="_Test Sales Taxes and Charges Template 1 - _TC",
			priority=2,
			save=1,
		)

		self.assertEqual(
			get_tax_template("2015-01-01", {"customer": "_Test Customer", "shipping_state": "Test State"}),
			"_Test Sales Taxes and Charges Template - _TC",
		)

	def test_select_tax_rule_based_on_better_priority(self):
		make_tax_rule(
			customer="_Test Customer",
			billing_city="Test City",
			sales_tax_template="_Test Sales Taxes and Charges Template - _TC",
			priority=1,
			save=1,
		)

		make_tax_rule(
			customer="_Test Customer",
			billing_city="Test City",
			sales_tax_template="_Test Sales Taxes and Charges Template 1 - _TC",
			priority=2,
			save=1,
		)

		self.assertEqual(
			get_tax_template("2015-01-01", {"customer": "_Test Customer", "billing_city": "Test City"}),
			"_Test Sales Taxes and Charges Template 1 - _TC",
		)

	def test_select_tax_rule_based_cross_matching_keys(self):
		make_tax_rule(
			customer="_Test Customer",
			billing_city="Test City",
			sales_tax_template="_Test Sales Taxes and Charges Template - _TC",
			save=1,
		)

		make_tax_rule(
			customer="_Test Customer 1",
			billing_city="Test City 1",
			sales_tax_template="_Test Sales Taxes and Charges Template 1 - _TC",
			save=1,
		)

		self.assertEqual(
			get_tax_template("2015-01-01", {"customer": "_Test Customer", "billing_city": "Test City 1"}),
			None,
		)

	def test_select_tax_rule_based_cross_partially_keys(self):
		make_tax_rule(
			customer="_Test Customer",
			billing_city="Test City",
			sales_tax_template="_Test Sales Taxes and Charges Template - _TC",
			save=1,
		)

		make_tax_rule(
			billing_city="Test City 1",
			sales_tax_template="_Test Sales Taxes and Charges Template 1 - _TC",
			save=1,
		)

		self.assertEqual(
			get_tax_template("2015-01-01", {"customer": "_Test Customer", "billing_city": "Test City 1"}),
			"_Test Sales Taxes and Charges Template 1 - _TC",
		)

	def test_taxes_fetch_via_tax_rule(self):
		make_tax_rule(
			customer="_Test Customer",
			billing_city="_Test City",
			sales_tax_template="_Test Sales Taxes and Charges Template - _TC",
			save=1,
		)

		# create opportunity for customer
		opportunity = make_opportunity(with_items=1)

		# make quotation from opportunity
		quotation = make_quotation(opportunity.name)
		quotation.save()

		self.assertEqual(quotation.taxes_and_charges, "_Test Sales Taxes and Charges Template - _TC")

		# Check if accounts heads and rate fetched are also fetched from tax template or not
		self.assertTrue(len(quotation.taxes) > 0)


def make_tax_rule(**args):
	args = frappe._dict(args)

	tax_rule = frappe.new_doc("Tax Rule")

	for key, val in args.items():
		if key != "save":
			tax_rule.set(key, val)

	tax_rule.company = args.company or "_Test Company"

	if args.save:
		tax_rule.insert()

	return tax_rule
