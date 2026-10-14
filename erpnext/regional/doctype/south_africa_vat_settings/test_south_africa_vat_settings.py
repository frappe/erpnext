# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe

from erpnext.regional.south_africa.setup import add_permissions
from erpnext.tests.utils import ERPNextTestSuite

COMPANY = "_Test Company SA VAT"


class TestSouthAfricaVATSettings(ERPNextTestSuite):
	def test_settings_accept_only_ledger_accounts_of_the_company(self):
		vat_account = get_account(COMPANY)
		group_account = frappe.db.get_value("Account", {"company": COMPANY, "is_group": 1})
		invalid_accounts = (
			[None],
			[get_account("_Test Company")],
			[group_account],
			[vat_account, vat_account],
		)
		for accounts in invalid_accounts:
			with self.subTest(accounts=accounts):
				self.assertRaises(frappe.ValidationError, make_settings(accounts).insert)

		make_settings([vat_account]).insert()

	@patch("erpnext.setup.doctype.company.company.install_country_fixtures")
	def test_company_cannot_be_changed(self, install_country_fixtures):
		other_company = frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": "_Test SA Other",
				"abbr": "_TSAO",
				"default_currency": "ZAR",
				"country": "South Africa",
			}
		).insert()
		settings = make_settings([get_account(COMPANY)]).insert()

		settings.company = other_company.name
		settings.vat_accounts = []
		settings.append("vat_accounts", {"account": get_account(other_company.name)})
		self.assertRaises(frappe.ValidationError, settings.save)

	def test_regional_setup_does_not_share_the_settings_with_all_users(self):
		frappe.db.delete("Custom DocPerm", {"parent": "South Africa VAT Settings"})
		add_permissions()
		self.addCleanup(frappe.clear_cache, doctype="South Africa VAT Settings")

		roles = frappe.get_all(
			"Custom DocPerm", filters={"parent": "South Africa VAT Settings"}, pluck="role"
		)
		self.assertIn("Accounts User", roles)
		self.assertNotIn("All", roles)


def make_settings(accounts: list):
	frappe.delete_doc_if_exists("South Africa VAT Settings", COMPANY)
	return frappe.get_doc(
		{
			"doctype": "South Africa VAT Settings",
			"company": COMPANY,
			"vat_accounts": [{"account": account} for account in accounts],
		}
	)


def get_account(company: str) -> str:
	return frappe.db.get_value("Account", {"company": company, "account_type": "Tax", "is_group": 0})
