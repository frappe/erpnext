# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.tests.utils import FrappeTestCase, change_settings, if_app_installed

from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.doctype.tax_rule.tax_rule import ConflictingTaxRule, get_tax_template

test_records = frappe.get_test_records("Tax Rule")


class TestTaxRule(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
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

	@if_app_installed("erpnext_crm")
	def test_taxes_fetch_via_tax_rule(self):
		from erpnext_crm.erpnext_crm.doctype.opportunity.opportunity import make_quotation
		from erpnext_crm.erpnext_crm.doctype.opportunity.test_opportunity import make_opportunity

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

	def test_create_tax_rule_and_apply_to_sales_invoice_TC_ACC_101(self):
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")
		# Step 1: Create a tax rule for a customer with a sales tax template
		make_tax_rule(
			customer="_Test Customer",
			sales_tax_template="_Test Sales Taxes and Charges Template - _TC",
			save=1,
		)

		# Step 3: Create a sales invoice for the customer
		sales_invoice = create_sales_invoice(
			customer="_Test Customer",
			save=1,
		)

		# Step 4: Fetch the sales tax based on the created tax rule and check the tax rate applied
		applied_tax_template = sales_invoice.taxes_and_charges

		# Step 5: Assert that the correct tax template is applied based on the customer's tax rule
		self.assertEqual(
			applied_tax_template,
			"_Test Sales Taxes and Charges Template - _TC",
		)

	def test_create_tax_rule_and_apply_to_purchase_invoice_TC_ACC_102(self):
		company = "_Test Company"
		company_doc = frappe.get_doc("Company", company)
		if not company_doc.stock_received_but_not_billed:
			company_doc.stock_received_but_not_billed = "Stock Received But Not Billed - _TC"
			company_doc.save()
		# Step 1: Create a tax rule for a supplier with a sales tax template
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")
		if frappe.db.exists("Purchase Taxes and Charges Template", "GST 1 - _TC"):
			existing_templates = "GST 1 - _TC"
		else:
			purchase_tax_template = frappe.new_doc("Purchase Taxes and Charges Template")
			purchase_tax_template.company = "_Test Company"
			purchase_tax_template.title = "GST 1"
			purchase_tax_template.tax_category = "_Test Tax Category 1"
			purchase_tax_template.append(
				"taxes",
				{
					"category": "Total",
					"add_deduct_tax": "Add",
					"charge_type": "On Net Total",
					"account_head": "Stock In Hand - _TC",
					"rate": 100,
					"description": "GST",
				},
			)
			purchase_tax_template.flags.ignore_permissions = True
			purchase_tax_template.save()
			existing_templates = purchase_tax_template.name

		make_tax_rule(
			tax_type="Purchase",
			supplier="_Test Supplier",
			purchase_tax_template=existing_templates,
			save=1,
		)

		# Step 2: Create a purchase invoice for the supplier
		purchase_invoice = frappe.new_doc("Purchase Invoice")
		purchase_invoice.supplier = "_Test Supplier"
		purchase_invoice.company = "_Test Company"
		purchase_invoice.append(
			"items",
			{
				"item_code": "_Test Item",
				"qty": 1,
				"rate": 100,
			},
		)
		purchase_invoice.credit_to = "Creditors - _TC"
		purchase_invoice.currency = "INR"
		purchase_invoice.save()
		purchase_invoice.submit()

		# Step 3: Fetch the sales tax based on the created tax rule and check the tax rate applied
		applied_tax_template = purchase_invoice.taxes_and_charges

		# Step 4: Assert that the correct tax template is applied based on the supplier's tax rule
		self.assertEqual(
			applied_tax_template,
			existing_templates,
		)


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
