# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import getdate, nowdate

from erpnext.accounts.utils import get_fiscal_year


class ShareholdingTestCase(IntegrationTestCase):
	def setUp(self):
		self.holder_count = 0
		if not frappe.db.exists("Warehouse Type", "Transit"):
			frappe.get_doc({"doctype": "Warehouse Type", "name": "Transit"}).insert()

		self.company = self.create_company("_Test Equity Accounting", "EQA")
		if not get_fiscal_year(nowdate(), company=self.company, raise_on_missing=False):
			year = getdate(nowdate()).year
			frappe.get_doc(
				{
					"doctype": "Fiscal Year",
					"year": f"_Test Equity Accounting FY {year}",
					"year_start_date": f"{year}-01-01",
					"year_end_date": f"{year}-12-31",
					"companies": [{"company": self.company}],
				}
			).insert()
		self.company_abbr = "EQA"
		self.cash = frappe.db.get_value(
			"Account", {"company": self.company, "account_type": "Cash", "is_group": 0}, "name"
		)
		self.equity_parent_account = frappe.db.get_value(
			"Account",
			{"company": self.company, "root_type": "Liability", "is_group": 1},
			"name",
			order_by="lft desc",
		)
		self.share_capital_account = self.create_equity_account("Test Share Capital")
		self.securities_premium_account = self.create_equity_account("Test Securities Premium")
		self.treasury_shares_account = self.create_equity_account("Test Treasury Shares")
		self.equity_adjustment_account = self.create_equity_account("Test Equity Adjustment")
		self.share_class = self.create_share_class()
		settings_name = frappe.db.get_value("Equity Accounting Settings", {"company": self.company})
		settings = (
			frappe.get_doc("Equity Accounting Settings", settings_name)
			if settings_name
			else frappe.new_doc("Equity Accounting Settings")
		)
		settings.update(
			{
				"company": self.company,
				"cash_or_bank_account": self.cash,
				"share_capital_account": self.share_capital_account,
				"securities_premium_account": self.securities_premium_account,
				"treasury_shares_account": self.treasury_shares_account,
				"equity_adjustment_account": self.equity_adjustment_account,
			}
		)
		settings.save()

	def create_company(self, company_name, abbreviation):
		if frappe.db.exists("Company", company_name):
			company = frappe.get_doc("Company", company_name)
		else:
			company = frappe.get_doc(
				{
					"doctype": "Company",
					"company_name": company_name,
					"abbr": abbreviation,
					"country": "India",
					"default_currency": "INR",
					"create_chart_of_accounts_based_on": "Standard Template",
					"chart_of_accounts": "Standard",
				}
			).insert()

		if not frappe.db.exists("Account", {"company": company.name}):
			company.create_default_accounts()
		return company.name

	def create_transaction(self, **values):
		transaction = frappe.get_doc(
			{
				"doctype": "Share Transaction",
				"company": self.company,
				"share_class": self.share_class,
				"posting_date": nowdate(),
				**values,
			}
		)
		transaction.insert()
		transaction.submit()
		return transaction

	def create_shareholder(self):
		self.holder_count += 1
		unique_value = f"{self._testMethodName}-{self.holder_count}"
		return (
			frappe.get_doc(
				{
					"doctype": "Shareholder",
					"legal_name": f"Test Holder {unique_value}",
					"shareholder_type": "Individual",
					"tax_id_type": "Test Tax ID",
					"tax_id": unique_value,
					"tax_id_country": "India",
				}
			)
			.insert()
			.name
		)

	def create_share_class(self):
		unique_value = self._testMethodName
		return (
			frappe.get_doc(
				{
					"doctype": "Share Class",
					"class_name": f"Test Ordinary {unique_value}",
					"class_code": unique_value,
					"category": "Ordinary",
					"has_dividend_rights": 0,
					"has_voting_rights": 1,
					"votes_per_share": 1,
				}
			)
			.insert()
			.name
		)

	def create_equity_account(self, account_name):
		if existing_account := frappe.db.get_value(
			"Account", {"account_name": account_name, "company": self.company}, "name"
		):
			return existing_account

		return (
			frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": account_name,
					"parent_account": self.equity_parent_account,
					"company": self.company,
					"account_currency": "INR",
				}
			)
			.insert()
			.name
		)

	def assert_accounting_rows(self, journal_entry, expected):
		actual = {
			row.account: (row.debit_in_account_currency, row.credit_in_account_currency)
			for row in journal_entry.accounts
		}
		self.assertEqual(actual, expected)
