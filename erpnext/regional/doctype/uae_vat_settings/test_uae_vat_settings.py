# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe

from erpnext.regional.united_arab_emirates.utils import get_tax_accounts
from erpnext.tests.utils import ERPNextTestSuite

COMPANY = "_Test Company UAE VAT"


class TestUAEVATSettings(ERPNextTestSuite):
	def test_settings_accept_only_ledger_accounts_of_a_uae_company(self):
		vat_account = get_account(COMPANY)
		group_account = frappe.db.get_value("Account", {"company": COMPANY, "is_group": 1})
		invalid_cases = (
			("_Test Company", [get_account("_Test Company")]),
			(COMPANY, [None]),
			(COMPANY, [get_account("_Test Company")]),
			(COMPANY, [group_account]),
			(COMPANY, [vat_account, vat_account]),
		)
		for company, accounts in invalid_cases:
			with self.subTest(company=company, accounts=accounts):
				self.assertRaises(frappe.ValidationError, make_settings(company, accounts).insert)

		make_settings(COMPANY, [vat_account]).insert()

	@patch("erpnext.setup.doctype.company.company.install_country_fixtures")
	def test_settings_follow_a_company_rename(self, install_country_fixtures):
		company = frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": "_Test UAE Rename",
				"abbr": "_TUR",
				"default_currency": "AED",
				"country": "United Arab Emirates",
			}
		).insert()
		vat_account = frappe.db.get_value("Account", {"company": company.name, "account_type": "Tax"})
		make_settings(company.name, [vat_account]).insert()

		frappe.rename_doc("Company", company.name, "_Test UAE Renamed")

		self.assertEqual(list(get_tax_accounts("_Test UAE Renamed")), [vat_account])


def make_settings(company: str, accounts: list):
	frappe.delete_doc_if_exists("UAE VAT Settings", company)
	return frappe.get_doc(
		{
			"doctype": "UAE VAT Settings",
			"company": company,
			"uae_vat_accounts": [{"account": account} for account in accounts],
		}
	)


def get_account(company: str) -> str:
	return frappe.db.get_value("Account", {"company": company, "account_type": "Tax", "is_group": 0})
