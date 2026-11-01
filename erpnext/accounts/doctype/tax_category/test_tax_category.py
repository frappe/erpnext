# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.accounts.doctype.tax_rule.tax_rule import get_tax_template
from erpnext.accounts.doctype.tax_rule.test_tax_rule import make_tax_rule
from erpnext.accounts.party import get_address_tax_category
from erpnext.tests.utils import ERPNextTestSuite

DISABLED_CATEGORY = "_Test Tax Category 1"
ENABLED_CATEGORY = "_Test Tax Category 2"


class TestTaxCategory(ERPNextTestSuite):
	def setUp(self):
		frappe.db.set_single_value(
			"Accounts Settings", "determine_address_tax_category_from", "Billing Address"
		)
		frappe.db.set_value("Tax Category", DISABLED_CATEGORY, "disabled", 1)

	def test_disabled_party_tax_category_is_ignored(self):
		self.assertEqual(get_address_tax_category(DISABLED_CATEGORY), "")
		self.assertEqual(get_address_tax_category(ENABLED_CATEGORY), ENABLED_CATEGORY)

	def test_disabled_address_tax_category_falls_back_to_party(self):
		address = frappe.get_doc(
			{
				"doctype": "Address",
				"address_title": "_Test Disabled Tax Category Address",
				"address_type": "Billing",
				"address_line1": "1 Tax Road",
				"city": "Tax City",
				"country": "India",
				"tax_category": DISABLED_CATEGORY,
			}
		).insert()

		self.assertEqual(
			get_address_tax_category(ENABLED_CATEGORY, billing_address=address.name), ENABLED_CATEGORY
		)

	def test_tax_rule_ignores_disabled_tax_category(self):
		frappe.db.delete("Tax Rule")
		make_tax_rule(
			customer="_Test Customer",
			tax_category=DISABLED_CATEGORY,
			sales_tax_template="_Test Sales Taxes and Charges Template - _TC",
			save=1,
		)

		self.assertIsNone(
			get_tax_template("2015-01-01", {"customer": "_Test Customer", "tax_category": DISABLED_CATEGORY})
		)
