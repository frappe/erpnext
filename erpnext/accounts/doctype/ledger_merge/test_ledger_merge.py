# Copyright (c) 2021, Wahni Green Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import ANY, patch

import frappe

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

		with patch("frappe.publish_realtime") as publish_realtime:
			start_merge(doc.name)

		parent = frappe.db.get_value("Account", "Administrative Test Expenses - _TC", "parent_account")
		self.assertEqual(parent, "Indirect Expenses - _TC")
		# only users who can open the Ledger Merge are told about it
		for event in ("ledger_merge_progress", "ledger_merge_refresh"):
			publish_realtime.assert_any_call(event, ANY, doctype="Ledger Merge", docname=doc.name)

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
