# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.accounts.party import DuplicatePartyAccountError, get_party_account, get_party_advance_account
from erpnext.tests.utils import ERPNextTestSuite


class TestSupplierGroup(ERPNextTestSuite):
	def test_duplicate_account_companies(self):
		group = self.make_group().insert()
		for account in ("Creditors - _TC", "_Test Payable - _TC"):
			group.append("accounts", {"company": "_Test Company", "account": account})

		self.assertRaises(DuplicatePartyAccountError, group.save)

	def test_accounts_must_belong_to_row_company(self):
		for field in ("account", "advance_account"):
			with self.subTest(field=field):
				group = self.make_group([{"company": "_Test Company", field: "Creditors - _TC1"}])
				self.assertRaisesRegex(frappe.ValidationError, "does not belong", group.insert)

	def test_accounts_must_be_leaf_accounts(self):
		for field in ("account", "advance_account"):
			with self.subTest(field=field):
				group = self.make_group([{"company": "_Test Company", field: "Current Liabilities - _TC"}])
				self.assertRaisesRegex(frappe.ValidationError, "account group", group.insert)

	def test_accounts_must_be_enabled(self):
		account = frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": frappe.generate_hash(),
				"company": "_Test Company",
				"parent_account": "Current Liabilities - _TC",
				"account_type": "Payable",
				"disabled": 1,
			}
		).insert()
		for field in ("account", "advance_account"):
			with self.subTest(field=field):
				group = self.make_group([{"company": "_Test Company", field: account.name}])
				self.assertRaisesRegex(frappe.ValidationError, "disabled", group.insert)

	def test_accounts_must_be_payable(self):
		for field in ("account", "advance_account"):
			with self.subTest(field=field):
				group = self.make_group([{"company": "_Test Company", field: "Debtors - _TC"}])
				self.assertRaisesRegex(frappe.ValidationError, "must be a Payable account", group.insert)

	def test_payable_and_advance_currency_must_match(self):
		group = self.make_group(
			[
				{
					"company": "_Test Company",
					"account": "Creditors - _TC",
					"advance_account": "Advance Paid USD - _TC",
				}
			]
		)
		self.assertRaisesRegex(frappe.ValidationError, "same currency", group.insert)

	def test_valid_accounts_are_inherited_by_company(self):
		group = self.make_group(
			[
				{
					"company": "_Test Company",
					"account": "_Test Payable - _TC",
					"advance_account": "Advance Paid - _TC",
				},
				{"company": "_Test Company 1"},
			]
		).insert()
		group.accounts[1].account = "_Test Payable - _TC1"
		group.save()
		supplier = frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": frappe.generate_hash(),
				"supplier_group": group.name,
				"supplier_type": "Company",
			}
		).insert()

		self.assertEqual(get_party_account("Supplier", supplier.name, "_Test Company"), "_Test Payable - _TC")
		self.assertEqual(
			get_party_advance_account("Supplier", supplier.name, "_Test Company"), "Advance Paid - _TC"
		)
		self.assertEqual(
			get_party_account("Supplier", supplier.name, "_Test Company 1"), "_Test Payable - _TC1"
		)

	@staticmethod
	def make_group(accounts=None):
		return frappe.get_doc(
			{
				"doctype": "Supplier Group",
				"supplier_group_name": frappe.generate_hash(),
				"accounts": accounts or [],
			}
		)
