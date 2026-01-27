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


class TestValidateEntries(IntegrationTestCase):
	"""
	Unit tests for validate_entries function.

	Regression test for #52018: parent_account_name should use account_key format.
	"""

	def test_adds_new_entry_to_accounts(self):
		"""
		Test that validate_entries adds a new entry to accounts_by_name
		when the key doesn't exist.
		"""
		entry = frappe._dict(
			{
				"account": "1000 - Test Account - ABC",
				"account_name": "Test Account",
				"account_number": "1000",
			}
		)

		key = "1000 - Test Account"
		accounts_by_name = {}
		accounts = []

		validate_entries(key, entry, accounts_by_name, accounts)

		# Verify account was added
		self.assertIn(key, accounts_by_name)
		self.assertEqual(len(accounts), 1)

	def test_does_not_duplicate_existing_entry(self):
		"""
		Test that validate_entries doesn't add duplicate entries.
		"""
		existing = frappe._dict(
			{
				"account_name": "Test Account",
				"account_key": "1000 - Test Account",
			}
		)

		entry = frappe._dict(
			{
				"account": "1000 - Test Account - ABC",
				"account_name": "Test Account",
				"account_number": "1000",
			}
		)

		key = "1000 - Test Account"
		accounts_by_name = {key: existing}
		accounts = [existing]

		validate_entries(key, entry, accounts_by_name, accounts)

		# Should still only have one entry
		self.assertEqual(len(accounts), 1)

	def test_sets_parent_account_name_with_account_number_format(self):
		"""
		Test that dynamically added accounts get parent_account_name
		in account_key format (with account number prefix).

		This test requires _Test Company with numbered accounts.
		"""
		# Skip if _Test Company doesn't exist
		if not frappe.db.exists("Company", "_Test Company"):
			self.skipTest("_Test Company does not exist")

		# Find an actual account with account_number to use as parent
		parent_account = frappe.db.get_value(
			"Account",
			{"company": "_Test Company", "account_number": ["is", "set"], "is_group": 1},
			["name", "account_name", "account_number"],
			as_dict=True,
		)

		if not parent_account:
			self.skipTest("No numbered parent account found in _Test Company")

		# Create a mock entry that references this parent
		entry = frappe._dict(
			{
				"account": parent_account.name,
				"account_name": parent_account.account_name,
				"account_number": parent_account.account_number,
			}
		)

		# Create key in account_key format
		key = f"{parent_account.account_number} - {parent_account.account_name}"

		accounts_by_name = {}
		accounts = []

		# This should add the account to accounts_by_name with proper parent_account_name
		validate_entries(key, entry, accounts_by_name, accounts)

		# Verify account was added
		self.assertIn(key, accounts_by_name)

		# If the account has a parent, verify parent_account_name format
		added_account = accounts_by_name[key]
		if added_account.get("parent_account") and added_account.get("parent_account_name"):
			# parent_account_name should contain " - " if parent has account_number
			parent_info = frappe.db.get_value(
				"Account",
				added_account.parent_account,
				["account_name", "account_number"],
				as_dict=True,
			)
			if parent_info and parent_info.account_number:
				expected = f"{parent_info.account_number} - {parent_info.account_name}"
				self.assertEqual(added_account.parent_account_name, expected)
