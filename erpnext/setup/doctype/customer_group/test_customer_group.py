# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from erpnext.accounts.party import DuplicatePartyAccountError
from erpnext.tests.utils import ERPNextTestSuite


class TestCustomerGroup(ERPNextTestSuite):
	def test_group_name_cannot_match_customer_on_insert_or_rename(self):
		customer = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": "_Test Group Name Collision",
				"customer_type": "Individual",
			}
		).insert()
		group = frappe.get_doc(
			{"doctype": "Customer Group", "customer_group_name": customer.name, "is_group": 0}
		)
		with self.assertRaises(frappe.NameError):
			group.insert()

		group.customer_group_name = "_Test Group To Rename"
		group.insert()
		with self.assertRaises(frappe.NameError):
			frappe.rename_doc("Customer Group", group.name, customer.name)

	def test_duplicate_credit_limit_company(self):
		group = frappe.get_doc(
			{
				"doctype": "Customer Group",
				"customer_group_name": "_Test Duplicate Group Limits",
				"is_group": 0,
			}
		)
		group.append("credit_limits", {"company": "_Test Company", "credit_limit": 100})
		group.append("credit_limits", {"company": "_Test Company", "credit_limit": 100000})
		with self.assertRaises(frappe.ValidationError):
			group.insert()

	def test_buying_price_list_cannot_be_group_default(self):
		group = frappe.get_doc(
			{
				"doctype": "Customer Group",
				"customer_group_name": "_Test Buying Price Group",
				"is_group": 0,
				"default_price_list": "Standard Buying",
			}
		)
		with self.assertRaises(frappe.ValidationError):
			group.insert()

	def test_leaf_with_customers_cannot_become_group(self):
		group = frappe.get_doc(
			{"doctype": "Customer Group", "customer_group_name": "_Test Leaf With Customer", "is_group": 0}
		).insert()
		frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": "_Test Customer In Leaf",
				"customer_type": "Individual",
				"customer_group": group.name,
			}
		).insert()
		group.is_group = 1
		with self.assertRaises(frappe.ValidationError):
			group.save()

	def test_invalid_party_accounts(self):
		group = frappe.new_doc("Customer Group")
		group.customer_group_name = "_Test Invalid Group Accounts"
		group.is_group = 0
		group.append("accounts", {"company": "_Test Company", "account": "Creditors - _TC"})
		with self.assertRaises(frappe.ValidationError):
			group.insert()

		group.accounts = []
		group.append("accounts", {"company": "_Test Company", "account": "Accounts Receivable - _TC"})
		with self.assertRaises(frappe.ValidationError):
			group.insert()

		group.accounts = []
		group.append("accounts", {"company": "_Test Company", "account": "Debtors - _TC"})
		group.append("accounts", {"company": "_Test Company", "account": "Debtors - _TC"})
		with self.assertRaises(DuplicatePartyAccountError):
			group.insert()

		group.accounts = []
		group.append("accounts", {"company": "_Test Company", "account": "Debtors - _TC"})
		group.insert()
