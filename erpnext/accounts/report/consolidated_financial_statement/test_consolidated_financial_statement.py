# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

"""
Tests for Consolidated Financial Statement report.

Regression tests for:
- #52018: KeyError when parent_account_name is None
- #49771: KeyError: None in accumulate_values_into_parents
"""

import frappe
from frappe.tests import IntegrationTestCase

from erpnext.accounts.report.consolidated_financial_statement.consolidated_financial_statement import (
	accumulate_values_into_parents,
	update_parent_account_names,
	validate_entries,
)


class TestAccumulateValuesIntoParents(IntegrationTestCase):
	"""
	Unit tests for accumulate_values_into_parents function.

	Regression test for #52018, #49771: KeyError when parent_account_name is None.
	"""

	def test_skips_account_with_none_parent_account_name(self):
		"""
		Test that accounts with parent_account_name=None are skipped
		without raising KeyError.
		"""
		# Account with parent_account but parent_account_name is None
		# This can happen when parent wasn't in fetched accounts
		accounts = [
			frappe._dict(
				{
					"account_name": "Test Account",
					"account_key": "Test Account",
					"parent_account": "Some Parent - ABC",  # Has parent_account
					"parent_account_name": None,  # But parent_account_name is None
					"company_wise_opening_bal": {},
				}
			),
		]

		accounts_by_name = {
			"Test Account": accounts[0],
		}

		companies = ["Test Company"]

		# This should not raise KeyError: None
		accumulate_values_into_parents(accounts, accounts_by_name, companies)

	def test_skips_account_with_missing_parent_in_accounts_by_name(self):
		"""
		Test that accounts whose parent_account_name is not in accounts_by_name
		are skipped without raising KeyError.
		"""
		accounts = [
			frappe._dict(
				{
					"account_name": "Child Account",
					"account_key": "Child Account",
					"parent_account": "Parent Account - ABC",
					"parent_account_name": "Parent Account",  # Parent exists
					"company_wise_opening_bal": {},
				}
			),
		]

		# Parent is NOT in accounts_by_name
		accounts_by_name = {
			"Child Account": accounts[0],
		}

		companies = ["Test Company"]

		# This should not raise KeyError: 'Parent Account'
		accumulate_values_into_parents(accounts, accounts_by_name, companies)

	def test_accumulates_values_when_parent_exists(self):
		"""
		Test that values are correctly accumulated when parent exists.
		"""
		child = frappe._dict(
			{
				"account_name": "Child Account",
				"account_key": "1100 - Child Account",
				"parent_account": "Parent Account - ABC",
				"parent_account_name": "1000 - Parent Account",
				"company_wise_opening_bal": {"Test Company": 100.0},
				"opening_balance": 100.0,
				"Test Company": 500.0,
			}
		)

		parent = frappe._dict(
			{
				"account_name": "Parent Account",
				"account_key": "1000 - Parent Account",
				"parent_account": None,
				"parent_account_name": None,
				"company_wise_opening_bal": {"Test Company": 0.0},
				"opening_balance": 0.0,
				"Test Company": 0.0,
			}
		)

		accounts = [parent, child]

		accounts_by_name = {
			"1000 - Parent Account": parent,
			"1100 - Child Account": child,
		}

		companies = ["Test Company"]

		accumulate_values_into_parents(accounts, accounts_by_name, companies)

		# Parent should have accumulated child's values
		self.assertEqual(parent["Test Company"], 500.0)
		self.assertEqual(parent["opening_balance"], 100.0)
		self.assertEqual(parent["company_wise_opening_bal"]["Test Company"], 100.0)


class TestUpdateParentAccountNames(IntegrationTestCase):
	"""
	Unit tests for update_parent_account_names function.
	"""

	def test_sets_parent_account_name_with_account_number(self):
		"""
		Test that parent_account_name uses account_key format
		(with account_number prefix when present).
		"""
		parent = frappe._dict(
			{
				"name": "1000 - Assets - ABC",
				"account_name": "Assets",
				"account_number": "1000",
				"parent_account": None,
			}
		)

		child = frappe._dict(
			{
				"name": "1100 - Cash - ABC",
				"account_name": "Cash",
				"account_number": "1100",
				"parent_account": "1000 - Assets - ABC",
			}
		)

		accounts = [parent, child]
		accounts = update_parent_account_names(accounts)

		# Child's parent_account_name should use account_key format
		self.assertEqual(child.parent_account_name, "1000 - Assets")

	def test_sets_parent_account_name_without_account_number(self):
		"""
		Test that parent_account_name works when account has no number.
		"""
		parent = frappe._dict(
			{
				"name": "Assets - ABC",
				"account_name": "Assets",
				"account_number": None,
				"parent_account": None,
			}
		)

		child = frappe._dict(
			{
				"name": "Cash - ABC",
				"account_name": "Cash",
				"account_number": None,
				"parent_account": "Assets - ABC",
			}
		)

		accounts = [parent, child]
		accounts = update_parent_account_names(accounts)

		# Child's parent_account_name should be just account_name
		self.assertEqual(child.parent_account_name, "Assets")

	def test_returns_none_for_missing_parent(self):
		"""
		Test that parent_account_name is None when parent not in accounts list.
		"""
		child = frappe._dict(
			{
				"name": "1100 - Cash - ABC",
				"account_name": "Cash",
				"account_number": "1100",
				"parent_account": "Missing Parent - XYZ",  # Not in list
			}
		)

		accounts = [child]
		accounts = update_parent_account_names(accounts)

		# parent_account_name should be None since parent not found
		self.assertIsNone(child.parent_account_name)


class TestConsolidatedFinancialStatementRegression(IntegrationTestCase):
	"""
	Integration test for Consolidated Financial Statement report.

	Regression test for #52018, #49771: KeyError when child company has an account
	with a numbered parent that doesn't exist in the parent company's fetched accounts.

	This test creates the exact conditions that trigger the bug:
	1. Parent company with is_group=1
	2. Child company under parent
	3. Numbered accounts in child company
	4. GL entry in child for account not in parent's fetched accounts
	"""

	TEST_PARENT_COMPANY = "_Test CFS Parent Co"
	TEST_CHILD_COMPANY = "_Test CFS Child Co"

	@classmethod
	def setUpClass(cls):
		"""Create test companies and accounts that reproduce the bug scenario."""
		super().setUpClass()

		# Create parent company
		if not frappe.db.exists("Company", cls.TEST_PARENT_COMPANY):
			parent_company = frappe.get_doc(
				{
					"doctype": "Company",
					"company_name": cls.TEST_PARENT_COMPANY,
					"abbr": "TCFSP",
					"country": "United States",
					"default_currency": "USD",
					"is_group": 1,
				}
			)
			parent_company.insert(ignore_permissions=True)

		# Create child company under parent
		if not frappe.db.exists("Company", cls.TEST_CHILD_COMPANY):
			child_company = frappe.get_doc(
				{
					"doctype": "Company",
					"company_name": cls.TEST_CHILD_COMPANY,
					"abbr": "TCFSC",
					"country": "United States",
					"default_currency": "USD",
					"parent_company": cls.TEST_PARENT_COMPANY,
					"is_group": 0,
				}
			)
			child_company.insert(ignore_permissions=True)

		frappe.db.commit()

		# Find the Assets root account in child company (created automatically)
		cls.child_assets_account = frappe.db.get_value(
			"Account",
			{
				"company": cls.TEST_CHILD_COMPANY,
				"root_type": "Asset",
				"is_group": 1,
				"parent_account": ["is", "not set"],
			},
			"name",
		)

		# Add account number to the Assets account to create the bug condition
		if cls.child_assets_account:
			frappe.db.set_value(
				"Account", cls.child_assets_account, "account_number", "1000"
			)
			frappe.db.commit()

	@classmethod
	def tearDownClass(cls):
		"""Clean up test companies and all related data."""
		super().tearDownClass()

		# Delete GL entries for test companies
		frappe.db.delete("GL Entry", {"company": cls.TEST_CHILD_COMPANY})
		frappe.db.delete("GL Entry", {"company": cls.TEST_PARENT_COMPANY})

		# Delete child company (accounts deleted via on_trash)
		if frappe.db.exists("Company", cls.TEST_CHILD_COMPANY):
			frappe.delete_doc("Company", cls.TEST_CHILD_COMPANY, force=True)

		# Delete parent company
		if frappe.db.exists("Company", cls.TEST_PARENT_COMPANY):
			frappe.delete_doc("Company", cls.TEST_PARENT_COMPANY, force=True)

		frappe.db.commit()

	def test_validate_entries_uses_account_key_format_for_parent(self):
		"""
		Test that validate_entries sets parent_account_name using account_key format.

		Bug scenario: Child company has account "99999 - Test Bank" under
		parent "1000 - Assets". When validate_entries dynamically adds this account,
		it must set parent_account_name to "1000 - Assets" (not just "Assets")
		to match the keys in accounts_by_name.
		"""
		# Create a child account with account number under the numbered parent
		test_account_name = f"_Test Bank {frappe.generate_hash()[:6]}"
		test_account = frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": test_account_name,
				"account_number": "1999",
				"parent_account": self.child_assets_account,
				"company": self.TEST_CHILD_COMPANY,
				"account_type": "Bank",
				"is_group": 0,
			}
		)
		test_account.insert(ignore_permissions=True)

		try:
			# Simulate what happens during report generation
			entry = frappe._dict(
				{
					"account": test_account.name,
					"account_name": test_account_name,
					"account_number": "1999",
				}
			)

			key = f"1999 - {test_account_name}"
			accounts_by_name = {}
			accounts = []

			# This should set parent_account_name to "1000 - Application of Funds (Assets)"
			# not just "Application of Funds (Assets)"
			validate_entries(key, entry, accounts_by_name, accounts)

			self.assertIn(key, accounts_by_name)
			added_account = accounts_by_name[key]

			# The critical assertion: parent_account_name must include account number
			self.assertIsNotNone(added_account.get("parent_account_name"))
			self.assertIn("1000", added_account.parent_account_name)

		finally:
			frappe.delete_doc("Account", test_account.name, force=True)
			frappe.db.commit()

	def test_report_executes_without_keyerror(self):
		"""
		End-to-end test: Run the Consolidated Financial Statement report
		with the bug conditions and verify no KeyError is raised.

		This is the actual regression test for issues #52018 and #49771.
		"""
		from erpnext.accounts.report.consolidated_financial_statement.consolidated_financial_statement import (
			execute,
		)

		# Create a unique test account in child company
		test_account_name = f"_Test CFS Bank {frappe.generate_hash()[:6]}"
		test_account = frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": test_account_name,
				"account_number": "1888",
				"parent_account": self.child_assets_account,
				"company": self.TEST_CHILD_COMPANY,
				"account_type": "Bank",
				"is_group": 0,
			}
		)
		test_account.insert(ignore_permissions=True)

		try:
			# Create a GL entry to make this account appear in the report
			gl_entry = frappe.get_doc(
				{
					"doctype": "GL Entry",
					"posting_date": frappe.utils.today(),
					"account": test_account.name,
					"company": self.TEST_CHILD_COMPANY,
					"debit": 1000,
					"credit": 0,
					"debit_in_account_currency": 1000,
					"credit_in_account_currency": 0,
					"voucher_type": "Journal Entry",
					"voucher_no": f"TEST-JV-{frappe.generate_hash()[:8]}",
					"is_opening": "No",
					"is_advance": "No",
				}
			)
			gl_entry.flags.ignore_permissions = True
			gl_entry.db_insert()
			frappe.db.commit()

			# Run the consolidated financial statement report
			filters = frappe._dict(
				{
					"company": self.TEST_PARENT_COMPANY,
					"report": "Balance Sheet",
					"period_start_date": frappe.utils.add_months(frappe.utils.today(), -1),
					"period_end_date": frappe.utils.today(),
					"periodicity": "Monthly",
					"accumulated_in_group_company": 0,
					"include_default_book_entries": 1,
				}
			)

			# This should NOT raise KeyError
			try:
				result = execute(filters)
				# execute returns (columns, data, message, chart, report_summary)
				self.assertIsNotNone(result)
				self.assertIsNotNone(result[0])  # columns
			except KeyError as e:
				self.fail(
					f"KeyError raised: {e}. "
					f"This is the bug from #52018/#49771 - parent_account_name format mismatch."
				)

		finally:
			# Cleanup
			frappe.db.delete("GL Entry", {"account": test_account.name})
			frappe.delete_doc("Account", test_account.name, force=True)
			frappe.db.commit()
