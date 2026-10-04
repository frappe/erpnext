# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import nowdate

from erpnext.accounts.doctype.tax_rule.tax_rule import ConflictingTaxRule, get_tax_template
from erpnext.crm.doctype.opportunity.mapper import make_quotation
from erpnext.crm.doctype.opportunity.test_opportunity import make_opportunity
from erpnext.tests.permission_test_utils import (
	as_user,
	assert_refused,
	assert_refused_for_names,
	assert_refused_without,
	make_fenced_user,
	malformed_names,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestTaxRule(ERPNextTestSuite):
	def setUp(self):
		frappe.db.set_single_value("Shopping Cart Settings", "enabled", 0)

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

	def test_for_parent_supplier_group(self):
		purchase_template = "_Test Purchase Taxes and Charges Template - _TC"
		make_tax_rule(
			supplier_group="All Supplier Groups",
			tax_type="Purchase",
			purchase_tax_template=purchase_template,
			priority=1,
			use_for_shopping_cart=0,
			from_date="2015-01-01",
			save=1,
		)

		# "_Test Supplier Group" has "All Supplier Groups" as its parent — should match hierarchically
		self.assertEqual(
			get_tax_template(
				"2015-01-01",
				{
					"supplier_group": "_Test Supplier Group",
					"tax_type": "Purchase",
					"use_for_shopping_cart": 0,
				},
			),
			purchase_template,
		)

	def test_use_for_shopping_cart_filter(self):
		city = "Test Cart City"
		# higher priority ensures this rule wins when use_for_shopping_cart is not filtered
		make_tax_rule(
			customer="_Test Customer",
			billing_city=city,
			sales_tax_template="_Test Sales Taxes and Charges Template - _TC",
			use_for_shopping_cart=0,
			priority=2,
			save=1,
		)
		make_tax_rule(
			customer="_Test Customer",
			billing_city=city,
			sales_tax_template="_Test Sales Taxes and Charges Template 1 - _TC",
			use_for_shopping_cart=1,
			priority=1,
			save=1,
		)

		# Cart request (use_for_shopping_cart=1) filters to cart rules only
		self.assertEqual(
			get_tax_template(
				"2015-01-01",
				{"customer": "_Test Customer", "billing_city": city, "use_for_shopping_cart": 1},
			),
			"_Test Sales Taxes and Charges Template 1 - _TC",
		)

		# Non-cart request omits use_for_shopping_cart — no filter is applied, both rules
		# are candidates; non-cart rule wins by higher priority
		self.assertEqual(
			get_tax_template(
				"2015-01-01",
				{"customer": "_Test Customer", "billing_city": city},
			),
			"_Test Sales Taxes and Charges Template - _TC",
		)

	def test_use_for_shopping_cart_default(self):
		city = "Test Default Cart City"
		# use_for_shopping_cart not set — Check field defaults to 0
		make_tax_rule(
			customer="_Test Customer",
			billing_city=city,
			sales_tax_template="_Test Sales Taxes and Charges Template - _TC",
			use_for_shopping_cart=0,  # Default is set to 1.
			save=1,
		)

		# Non-cart request (no use_for_shopping_cart in args) matches the rule
		self.assertEqual(
			get_tax_template(
				"2015-01-01",
				{"customer": "_Test Customer", "billing_city": city},
			),
			"_Test Sales Taxes and Charges Template - _TC",
		)

		# Cart request (use_for_shopping_cart=1) does not match — rule has default 0
		self.assertIsNone(
			get_tax_template(
				"2015-01-01",
				{"customer": "_Test Customer", "billing_city": city, "use_for_shopping_cart": 1},
			)
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
		self.assertGreater(len(quotation.taxes), 0)

	def make_customer_address(self):
		return (
			frappe.get_doc(
				{
					"doctype": "Address",
					"address_title": "UP Tax Rule Address",
					"address_type": "Billing",
					"address_line1": "1 Fence Road",
					"city": "Fence City",
					"country": "India",
					"is_primary_address": 1,
					"links": [{"link_doctype": "Customer", "link_name": "_Test Customer"}],
				}
			)
			.insert()
			.name
		)

	def test_get_party_details_checks_the_party_and_the_address(self):
		from erpnext.accounts.doctype.tax_rule.tax_rule import get_party_details

		address = self.make_customer_address()

		def party_kwargs(name):
			return {"party": name, "party_type": "Customer"}

		def address_kwargs(name):
			return {"party": "_Test Customer", "party_type": "Customer", "args": {"billing_address": name}}

		outside = make_fenced_user(
			"taxrule-fenced@example.com", ["Accounts User"], [("Customer", "_Test Customer 1")]
		)
		with as_user(outside):
			assert_refused(self, get_party_details, "_Test Customer", "customer")
			assert_refused(self, get_party_details, **address_kwargs(address))
			assert_refused_for_names(
				self, get_party_details, party_kwargs, [], type_gated=True, caller_supplied=True
			)
		unfenced = make_fenced_user("taxrule-unfenced@example.com", ["Accounts User"])
		with as_user(unfenced):
			assert_refused(self, get_party_details, unfenced, "User")
			assert_refused(self, get_party_details, "_Test Customer", "")
			for name in malformed_names():
				if isinstance(name, str):
					self.assertRaises(frappe.DoesNotExistError, get_party_details, **address_kwargs(name))
				else:
					self.assertRaises(frappe.PermissionError, get_party_details, **address_kwargs(name))
		inside = make_fenced_user(
			"taxrule-fenced@example.com", ["Accounts User"], [("Customer", "_Test Customer")]
		)
		with as_user(inside):
			self.assertEqual(get_party_details("_Test Customer", "customer")["billing_city"], "Fence City")

	def test_get_party_details_refuses_an_unreadable_address_but_set_taxes_still_works(self):
		from erpnext.accounts.doctype.tax_rule.tax_rule import get_party_details
		from erpnext.accounts.party import set_taxes

		address = self.make_customer_address()
		stock_user = make_fenced_user("taxrule-stock@example.com", ["Stock User"])
		with as_user(stock_user):
			assert_refused(
				self, get_party_details, "_Test Customer", "Customer", {"billing_address": address}
			)
			set_taxes("_Test Customer", "Customer", nowdate(), "_Test Company", billing_address=address)
		other_address = (
			frappe.get_doc(
				{
					"doctype": "Address",
					"address_title": "UP Tax Rule Other Address",
					"address_type": "Billing",
					"address_line1": "2 Fence Road",
					"city": "Fence City",
					"country": "India",
				}
			)
			.insert()
			.name
		)
		address_fenced = make_fenced_user(
			"taxrule-address@example.com",
			["Accounts User"],
			[("Customer", "_Test Customer"), ("Address", other_address)],
		)
		with as_user(address_fenced):
			assert_refused_without(self, [address], get_party_details, "_Test Customer", "Customer")


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
