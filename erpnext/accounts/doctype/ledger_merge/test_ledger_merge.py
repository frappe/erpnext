# Copyright (c) 2021, Wahni Green Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe

from erpnext.accounts.doctype.ledger_merge import ledger_merge
from erpnext.accounts.doctype.ledger_merge.ledger_merge import start_merge
from erpnext.tests.utils import ERPNextTestSuite


class TestLedgerMerge(ERPNextTestSuite):
	def test_merge_success(self):
		if not frappe.db.exists("Account", "Indirect Expenses - _TC"):
			acc = frappe.new_doc("Account")
			acc.account_name = "Indirect Expenses"
			acc.is_group = 1
			acc.parent_account = "Expenses - _TC"
			acc.company = "_Test Company"
			acc.insert()
		if not frappe.db.exists("Account", "Indirect Test Expenses - _TC"):
			acc = frappe.new_doc("Account")
			acc.account_name = "Indirect Test Expenses"
			acc.is_group = 1
			acc.parent_account = "Expenses - _TC"
			acc.company = "_Test Company"
			acc.insert()
		if not frappe.db.exists("Account", "Administrative Test Expenses - _TC"):
			acc = frappe.new_doc("Account")
			acc.account_name = "Administrative Test Expenses"
			acc.parent_account = "Indirect Test Expenses - _TC"
			acc.company = "_Test Company"
			acc.insert()

		doc = frappe.get_doc(
			{
				"doctype": "Ledger Merge",
				"company": "_Test Company",
				"root_type": frappe.db.get_value("Account", "Indirect Test Expenses - _TC", "root_type"),
				"account": "Indirect Expenses - _TC",
				"merge_accounts": [
					{"account": "Indirect Test Expenses - _TC", "account_name": "Indirect Expenses"}
				],
			}
		).insert(ignore_permissions=True)

		parent = frappe.db.get_value("Account", "Administrative Test Expenses - _TC", "parent_account")
		self.assertEqual(parent, "Indirect Test Expenses - _TC")

		start_merge(doc.name)

		parent = frappe.db.get_value("Account", "Administrative Test Expenses - _TC", "parent_account")
		self.assertEqual(parent, "Indirect Expenses - _TC")

		self.assertFalse(frappe.db.exists("Account", "Indirect Test Expenses - _TC"))

	def test_partial_merge_success(self):
		if not frappe.db.exists("Account", "Indirect Income - _TC"):
			acc = frappe.new_doc("Account")
			acc.account_name = "Indirect Income"
			acc.is_group = 1
			acc.parent_account = "Income - _TC"
			acc.company = "_Test Company"
			acc.insert()
		if not frappe.db.exists("Account", "Indirect Test Income - _TC"):
			acc = frappe.new_doc("Account")
			acc.account_name = "Indirect Test Income"
			acc.is_group = 1
			acc.parent_account = "Income - _TC"
			acc.company = "_Test Company"
			acc.insert()
		if not frappe.db.exists("Account", "Administrative Test Income - _TC"):
			acc = frappe.new_doc("Account")
			acc.account_name = "Administrative Test Income"
			acc.parent_account = "Indirect Test Income - _TC"
			acc.company = "_Test Company"
			acc.insert()

		doc = frappe.get_doc(
			{
				"doctype": "Ledger Merge",
				"company": "_Test Company",
				"root_type": frappe.db.get_value("Account", "Indirect Income - _TC", "root_type"),
				"account": "Indirect Income - _TC",
				"merge_accounts": [
					{"account": "Indirect Test Income - _TC", "account_name": "Indirect Test Income"},
					{
						"account": "Administrative Test Income - _TC",
						"account_name": "Administrative Test Income",
					},
				],
			}
		).insert(ignore_permissions=True)

		parent = frappe.db.get_value("Account", "Administrative Test Income - _TC", "parent_account")
		self.assertEqual(parent, "Indirect Test Income - _TC")

		start_merge(doc.name)

		parent = frappe.db.get_value("Account", "Administrative Test Income - _TC", "parent_account")
		self.assertEqual(parent, "Indirect Income - _TC")

		self.assertFalse(frappe.db.exists("Account", "Indirect Test Income - _TC"))
		self.assertTrue(frappe.db.exists("Account", "Administrative Test Income - _TC"))

	def test_retry_after_partial_merge(self):
		accounts = []
		for name in ("Retry Merge Target", "Retry Merge A", "Retry Merge B"):
			if not frappe.db.exists("Account", f"{name} - _TC"):
				frappe.get_doc(
					{
						"doctype": "Account",
						"account_name": name,
						"parent_account": "Indirect Expenses - _TC",
						"company": "_Test Company",
					}
				).insert()
			accounts.append(f"{name} - _TC")
		target, first, second = accounts

		doc = frappe.get_doc(
			{
				"doctype": "Ledger Merge",
				"company": "_Test Company",
				"root_type": "Expense",
				"account": target,
				"merge_accounts": [
					{"account": first, "account_name": first},
					{"account": second, "account_name": second},
				],
			}
		).insert(ignore_permissions=True)

		merge_account = ledger_merge.merge_account

		def fail_second(old, new):
			if old == second:
				frappe.throw("System In Use")
			return merge_account(old, new)

		with patch.object(ledger_merge, "merge_account", side_effect=fail_second):
			start_merge(doc.name)
		self.assertEqual(frappe.db.get_value("Ledger Merge", doc.name, "status"), "Partial Success")

		start_merge(doc.name)
		doc.reload()
		self.assertEqual(doc.status, "Success")
		self.assertEqual([row.merged for row in doc.merge_accounts], [1, 1])
		self.assertEqual([row.account_name for row in doc.merge_accounts], [first, second])
		self.assertFalse(frappe.db.exists("Account", second))

	def test_account_name_is_set_from_account(self):
		doc = frappe.get_doc(
			{
				"doctype": "Ledger Merge",
				"company": "_Test Company",
				"root_type": "Expense",
				"account": "Indirect Expenses - _TC",
				"merge_accounts": [{"account": "_Test Account Cost for Goods Sold - _TC"}],
			}
		).insert(ignore_permissions=True)
		self.assertEqual(doc.merge_accounts[0].account_name, "_Test Account Cost for Goods Sold - _TC")
