# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

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
