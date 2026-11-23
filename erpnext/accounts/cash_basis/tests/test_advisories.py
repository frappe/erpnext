# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Phase 8: a regional app replaces get_accounting_method_advisories (section 5.3)."""

import frappe

from erpnext.accounts.cash_basis import get_accounting_method_advisories, get_accounting_method_messages
from erpnext.accounts.cash_basis.tests.fixtures import (
	US_COMPANY,
	put_test_countries_in_scope,
	setup_cash_basis_master_data,
)
from erpnext.tests.utils import ERPNextTestSuite

REGION = "_Test Cash Basis Region"


class TestCashBasisAdvisories(ERPNextTestSuite):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		put_test_countries_in_scope(cls)
		setup_cash_basis_master_data()

	def setUp(self):
		if not frappe.db.exists("Country", REGION):
			# A test country has no ISO code, so the record skips the validation of Country.
			frappe.get_doc({"doctype": "Country", "country_name": REGION}).db_insert()

	def test_core_has_no_advice(self):
		self.assertEqual(get_accounting_method_messages(US_COMPANY)["advisories"], [])

	def test_regional_app_replaces_the_advisories(self):
		# The hook of the test app applies to the country of the company.
		country = frappe.db.get_value("Company", US_COMPANY, "country")
		frappe.db.set_value("Company", US_COMPANY, "country", REGION)
		previous = frappe.flags.company
		frappe.flags.company = "Other Company"
		try:
			messages = get_accounting_method_messages(US_COMPANY)
			self.assertEqual(
				messages["advisories"],
				[
					{
						"title": "Test advisory",
						"message": f"Regional advice for {US_COMPANY}, flag {US_COMPANY}",
						"indicator": "orange",
					}
				],
			)
			# The core notice stays, and the caller restores the flag.
			self.assertTrue(messages["notice"])
			self.assertEqual(frappe.flags.company, "Other Company")
		finally:
			frappe.flags.company = previous
			frappe.db.set_value("Company", US_COMPANY, "country", country)

	def test_the_flag_decides_the_country(self):
		# allow_regional reads frappe.flags.company, not the argument.
		country = frappe.db.get_value("Company", US_COMPANY, "country")
		frappe.db.set_value("Company", US_COMPANY, "country", REGION)
		previous = (frappe.flags.company, frappe.flags.country)
		frappe.flags.company = None
		frappe.flags.country = "United States"
		try:
			self.assertEqual(get_accounting_method_advisories(US_COMPANY), [])
		finally:
			frappe.flags.company, frappe.flags.country = previous
			frappe.db.set_value("Company", US_COMPANY, "country", country)
