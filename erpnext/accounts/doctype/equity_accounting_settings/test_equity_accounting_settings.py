# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from erpnext.accounts.doctype.equity_accounting_settings.equity_accounting_settings import (
	validate_account,
)


class TestEquityAccountingSettings(IntegrationTestCase):
	def setUp(self):
		self.company = "_Test Company"
		self.currency = frappe.db.get_value("Company", self.company, "default_currency")
		self.cash_account = frappe.db.get_value(
			"Account", {"company": self.company, "account_type": "Cash", "is_group": 0}
		)

	def test_company_cash_account_is_valid_for_settlement(self):
		validate_account(self.cash_account, self.company, self.currency, {"Asset"})

	def test_account_from_another_company_is_rejected(self):
		with self.assertRaisesRegex(frappe.ValidationError, "must belong to"):
			validate_account(self.cash_account, "_Test Company 2", self.currency, {"Asset"})

	def test_asset_account_cannot_be_used_for_share_capital(self):
		with self.assertRaisesRegex(frappe.ValidationError, "root type"):
			validate_account(self.cash_account, self.company, self.currency, {"Equity", "Liability"})

	def test_party_account_cannot_be_used_for_settlement(self):
		account = frappe.db.get_value(
			"Account",
			{
				"company": self.company,
				"account_type": "Receivable",
				"root_type": "Asset",
				"account_currency": self.currency,
				"is_group": 0,
			},
		)
		with self.assertRaisesRegex(frappe.ValidationError, "requires a party"):
			validate_account(account, self.company, self.currency, {"Asset"})

	def test_accounting_roles_cannot_share_an_account(self):
		account = frappe.db.get_value(
			"Account",
			{
				"company": self.company,
				"root_type": ["in", ["Equity", "Liability"]],
				"is_group": 0,
				"account_type": ["not in", ["Receivable", "Payable"]],
			},
		)
		self.assertIsNotNone(account)
		settings = frappe.get_doc(
			{
				"doctype": "Equity Accounting Settings",
				"company": self.company,
				"share_capital_account": account,
				"securities_premium_account": account,
			}
		)
		with self.assertRaisesRegex(frappe.ValidationError, "separate Account"):
			settings.validate()
