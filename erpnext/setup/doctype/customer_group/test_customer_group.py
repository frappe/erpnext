# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.permissions import setup_custom_perms

from erpnext.accounts.party import DuplicatePartyAccountError
from erpnext.tests.permission_test_utils import make_fenced_user
from erpnext.tests.utils import ERPNextTestSuite


class TestCustomerGroup(ERPNextTestSuite):
	def test_customer_role_can_only_select_customer_groups(self):
		group = frappe.get_doc(
			doctype="Customer Group", customer_group_name="_Test Portal Customer Group", is_group=0
		).insert()
		user = make_fenced_user("customer-group-portal@example.com", ["Customer"])
		with self.set_user(user):
			self.assertEqual(
				frappe.get_list("Customer Group", filters={"name": group.name}, pluck="name"), [group.name]
			)
			for permission in ("read", "print", "email", "export", "report", "share"):
				with self.subTest(permission=permission):
					self.assertFalse(frappe.has_permission("Customer Group", permission, doc=group))

	def test_customer_with_sales_master_role_can_edit_and_print_customer_groups(self):
		group = frappe.get_doc(
			doctype="Customer Group", customer_group_name="_Test Staff Customer Group", is_group=0
		).insert()
		user = make_fenced_user("customer-group-staff@example.com", ["Customer", "Sales Master Manager"])
		with self.set_user(user):
			group.check_permission("read")
			group.default_price_list = "Standard Selling"
			group.save()
			self.assertTrue(frappe.has_permission("Customer Group", "print", doc=group))
		self.assertEqual(group.reload().default_price_list, "Standard Selling")

	def test_customer_group_permission_upgrade_preserves_custom_access(self):
		from erpnext.patches.v16_0.restrict_customer_group_permissions import execute

		self.addCleanup(frappe.clear_cache, doctype="Customer Group")
		setup_custom_perms("Customer Group")
		legacy_rule = frappe.get_doc(
			"Custom DocPerm", {"parent": "Customer Group", "role": "Customer", "permlevel": 0}
		)
		output_permissions = ("print", "email", "export", "report", "share")
		legacy_rule.update(dict.fromkeys(output_permissions, 1)).save()
		frappe.copy_doc(legacy_rule).update({"read": 1, "if_owner": 1}).insert()
		frappe.copy_doc(legacy_rule).update({"parent": "Territory"}).insert()
		filters = {"parent": ["in", ("Customer Group", "Territory")], "name": ["!=", legacy_rule.name]}
		preserved_rules = frappe.get_all("Custom DocPerm", filters=filters, fields=["*"], order_by="name")

		execute()
		execute()

		legacy_rule.reload()
		self.assertEqual(legacy_rule.select, 1)
		for permission in output_permissions:
			with self.subTest(permission=permission):
				self.assertEqual(legacy_rule.get(permission), 0)
		self.assertEqual(
			frappe.get_all("Custom DocPerm", filters=filters, fields=["*"], order_by="name"), preserved_rules
		)

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

		group = frappe.get_doc(
			{"doctype": "Customer Group", "customer_group_name": "_Test Group To Rename", "is_group": 0}
		).insert()
		with self.assertRaises(frappe.NameError):
			frappe.rename_doc("Customer Group", group.name, customer.name)
		with self.assertRaises(frappe.NameError):
			frappe.rename_doc("Customer Group", group.name, f"  {customer.name}  ")

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

	def test_advance_account_without_receivable_account(self):
		group = frappe.get_doc(
			{
				"doctype": "Customer Group",
				"customer_group_name": "_Test Advance Only Group",
				"is_group": 0,
				"accounts": [{"company": "_Test Company", "advance_account": "Debtors - _TC"}],
			}
		).insert()
		self.assertFalse(group.accounts[0].account)
		self.assertEqual(group.accounts[0].advance_account, "Debtors - _TC")
