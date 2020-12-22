# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import unittest
import frappe
from erpnext.stock import get_warehouse_account, get_company_default_inventory_account
from erpnext.accounts.doctype.account.account import update_account_number, merge_account

class TestAccount(unittest.TestCase):
	def test_rename_account(self):
		if not frappe.db.exists("Account", "1210 - Debtors - _TC"):
			acc = frappe.new_doc("Account")
			acc.account_name = "Debtors"
			acc.parent_account = "Accounts Receivable - _TC"
			acc.account_number = "1210"
			acc.company = "_Test Company"
			acc.insert()

		account_number, account_name = frappe.db.get_value("Account", "1210 - Debtors - _TC",
			["account_number", "account_name"])
		self.assertEqual(account_number, "1210")
		self.assertEqual(account_name, "Debtors")

		new_account_number = "1211-11-4 - 6 - "
		new_account_name = "Debtors 1 - Test - "

		update_account_number("1210 - Debtors - _TC", new_account_name, new_account_number)

		new_acc = frappe.db.get_value("Account", "1211-11-4 - 6 - - Debtors 1 - Test - - _TC",
			["account_name", "account_number"], as_dict=1)

		self.assertEqual(new_acc.account_name, "Debtors 1 - Test -")
		self.assertEqual(new_acc.account_number, "1211-11-4 - 6 -")

		frappe.delete_doc("Account", "1211-11-4 - 6 - Debtors 1 - Test - - _TC")

	def test_merge_account(self):
		if not frappe.db.exists("Account", "Current Assets - _TC"):
			acc = frappe.new_doc("Account")
			acc.account_name = "Current Assets"
			acc.is_group = 1
			acc.parent_account = "Application of Funds (Assets) - _TC"
			acc.company = "_Test Company"
			acc.insert()
		if not frappe.db.exists("Account", "Securities and Deposits - _TC"):
			acc = frappe.new_doc("Account")
			acc.account_name = "Securities and Deposits"
			acc.parent_account = "Current Assets - _TC"
			acc.is_group = 1
			acc.company = "_Test Company"
			acc.insert()
		if not frappe.db.exists("Account", "Earnest Money - _TC"):
			acc = frappe.new_doc("Account")
			acc.account_name = "Earnest Money"
			acc.parent_account = "Securities and Deposits - _TC"
			acc.company = "_Test Company"
			acc.insert()
		if not frappe.db.exists("Account", "Cash In Hand - _TC"):
			acc = frappe.new_doc("Account")
			acc.account_name = "Cash In Hand"
			acc.is_group = 1
			acc.parent_account = "Current Assets - _TC"
			acc.company = "_Test Company"
			acc.insert()
		if not frappe.db.exists("Account", "Accumulated Depreciation - _TC"):
			acc = frappe.new_doc("Account")
			acc.account_name = "Accumulated Depreciation"
			acc.parent_account = "Fixed Assets - _TC"
			acc.company = "_Test Company"
			acc.account_type = "Accumulated Depreciation"
			acc.insert()

		doc = frappe.get_doc("Account", "Securities and Deposits - _TC")
		parent = frappe.db.get_value("Account", "Earnest Money - _TC", "parent_account")

		self.assertEqual(parent, "Securities and Deposits - _TC")

		merge_account("Securities and Deposits - _TC", "Cash In Hand - _TC", doc.is_group, doc.root_type, doc.company)
		parent = frappe.db.get_value("Account", "Earnest Money - _TC", "parent_account")

		# Parent account of the child account changes after merging
		self.assertEqual(parent, "Cash In Hand - _TC")

		# Old account doesn't exist after merging
		self.assertFalse(frappe.db.exists("Account", "Securities and Deposits - _TC"))

		doc = frappe.get_doc("Account", "Current Assets - _TC")

		# Raise error as is_group property doesn't match
		self.assertRaises(frappe.ValidationError, merge_account, "Current Assets - _TC",\
			"Accumulated Depreciation - _TC", doc.is_group, doc.root_type, doc.company)

		doc = frappe.get_doc("Account", "Capital Stock - _TC")

		# Raise error as root_type property doesn't match
		self.assertRaises(frappe.ValidationError, merge_account, "Capital Stock - _TC",\
			"Softwares - _TC", doc.is_group, doc.root_type, doc.company)

	def test_account_sync(self):
		frappe.local.flags.pop("ignore_root_company_validation", None)

		acc = frappe.new_doc("Account")
		acc.account_name = "Test Sync Account"
		acc.parent_account = "Temporary Accounts - _TC3"
		acc.company = "_Test Company 3"
		acc.insert()

		acc_tc_4 = frappe.db.get_value('Account', {'account_name': "Test Sync Account", "company": "_Test Company 4"})
		acc_tc_5 = frappe.db.get_value('Account', {'account_name': "Test Sync Account", "company": "_Test Company 5"})
		self.assertEqual(acc_tc_4, "Test Sync Account - _TC4")
		self.assertEqual(acc_tc_5, "Test Sync Account - _TC5")

	def test_add_account_to_a_group(self):
		frappe.db.set_value("Account", "Office Rent - _TC3", "is_group", 1)

		acc = frappe.new_doc("Account")
		acc.account_name = "Test Group Account"
		acc.parent_account = "Office Rent - _TC3"
		acc.company = "_Test Company 3"
		self.assertRaises(frappe.ValidationError, acc.insert)

		frappe.db.set_value("Account", "Office Rent - _TC3", "is_group", 0)

	def test_account_rename_sync(self):
		frappe.local.flags.pop("ignore_root_company_validation", None)

		acc = frappe.new_doc("Account")
		acc.account_name = "Test Rename Account"
		acc.parent_account = "Temporary Accounts - _TC3"
		acc.company = "_Test Company 3"
		acc.insert()

		# Rename account in parent company
		update_account_number(acc.name, "Test Rename Sync Account", "1234")

		# Check if renamed in children
		self.assertTrue(frappe.db.exists("Account", {'account_name': "Test Rename Sync Account", "company": "_Test Company 4", "account_number": "1234"}))
		self.assertTrue(frappe.db.exists("Account", {'account_name': "Test Rename Sync Account", "company": "_Test Company 5", "account_number": "1234"}))

		frappe.delete_doc("Account", "1234 - Test Rename Sync Account - _TC3")
		frappe.delete_doc("Account", "1234 - Test Rename Sync Account - _TC4")
		frappe.delete_doc("Account", "1234 - Test Rename Sync Account - _TC5")

	def test_child_company_account_rename_sync(self):
		frappe.local.flags.pop("ignore_root_company_validation", None)

		acc = frappe.new_doc("Account")
		acc.account_name = "Test Group Account"
		acc.parent_account = "Temporary Accounts - _TC3"
		acc.is_group = 1
		acc.company = "_Test Company 3"
		acc.insert()

		self.assertTrue(frappe.db.exists("Account", {'account_name': "Test Group Account", "company": "_Test Company 4"}))
		self.assertTrue(frappe.db.exists("Account", {'account_name': "Test Group Account", "company": "_Test Company 5"}))

		# Try renaming child company account
		acc_tc_5 = frappe.db.get_value('Account', {'account_name': "Test Group Account", "company": "_Test Company 5"})
		self.assertRaises(frappe.ValidationError, update_account_number, acc_tc_5, "Test Modified Account")

		# Rename child company account with allow_account_creation_against_child_company enabled
		frappe.db.set_value("Company", "_Test Company 5", "allow_account_creation_against_child_company", 1)

		update_account_number(acc_tc_5, "Test Modified Account")
		self.assertTrue(frappe.db.exists("Account", {'name': "Test Modified Account - _TC5", "company": "_Test Company 5"}))

		frappe.db.set_value("Company", "_Test Company 5", "allow_account_creation_against_child_company", 0)

		to_delete = ["Test Group Account - _TC3", "Test Group Account - _TC4", "Test Modified Account - _TC5"]
		for doc in to_delete:
			frappe.delete_doc("Account", doc)


def _make_test_records(verbose=None):
	from frappe.test_runner import make_test_objects

	accounts = [
		# [account_name, parent_account, is_group]
		["_Test Bank", "Bank Accounts", 0, "Bank", None],
		["_Test Bank USD", "Bank Accounts", 0, "Bank", "USD"],
		["_Test Bank EUR", "Bank Accounts", 0, "Bank", "EUR"],
		["_Test Cash", "Cash In Hand", 0, "Cash", None],

		["_Test Account Stock Expenses", "Direct Expenses", 1, None, None],
		["_Test Account Shipping Charges", "_Test Account Stock Expenses", 0, "Chargeable", None],
		["_Test Account Customs Duty", "_Test Account Stock Expenses", 0, "Tax", None],
		["_Test Account Insurance Charges", "_Test Account Stock Expenses", 0, "Chargeable", None],
		["_Test Account Stock Adjustment", "_Test Account Stock Expenses", 0, "Stock Adjustment", None],
		["_Test Employee Advance", "Current Liabilities", 0, None, None],

		["_Test Account Tax Assets", "Current Assets", 1, None, None],
		["_Test Account VAT", "_Test Account Tax Assets", 0, "Tax", None],
		["_Test Account Service Tax", "_Test Account Tax Assets", 0, "Tax", None],

		["_Test Account Reserves and Surplus", "Current Liabilities", 0, None, None],

		["_Test Account Cost for Goods Sold", "Expenses", 0, None, None],
		["_Test Account Excise Duty", "_Test Account Tax Assets", 0, "Tax", None],
		["_Test Account Education Cess", "_Test Account Tax Assets", 0, "Tax", None],
		["_Test Account S&H Education Cess", "_Test Account Tax Assets", 0, "Tax", None],
		["_Test Account CST", "Direct Expenses", 0, "Tax", None],
		["_Test Account Discount", "Direct Expenses", 0, None, None],
		["_Test Write Off", "Indirect Expenses", 0, None, None],
		["_Test Exchange Gain/Loss", "Indirect Expenses", 0, None, None],

		["_Test Account Sales", "Direct Income", 0, None, None],

		# related to Account Inventory Integration
		["_Test Account Stock In Hand", "Current Assets", 0, None, None],

		# fixed asset depreciation
		["_Test Fixed Asset", "Current Assets", 0, "Fixed Asset", None],
		["_Test Accumulated Depreciations", "Current Assets", 0, "Accumulated Depreciation", None],
		["_Test Depreciations", "Expenses", 0, None, None],
		["_Test Gain/Loss on Asset Disposal", "Expenses", 0, None, None],

		# Receivable / Payable Account
		["_Test Receivable", "Current Assets", 0, "Receivable", None],
		["_Test Payable", "Current Liabilities", 0, "Payable", None],
		["_Test Receivable USD", "Current Assets", 0, "Receivable", "USD"],
		["_Test Payable USD", "Current Liabilities", 0, "Payable", "USD"]
	]

	for company, abbr in [["_Test Company", "_TC"], ["_Test Company 1", "_TC1"], ["_Test Company with perpetual inventory", "TCP1"]]:
		test_objects = make_test_objects("Account", [{
				"doctype": "Account",
				"account_name": account_name,
				"parent_account": parent_account + " - " + abbr,
				"company": company,
				"is_group": is_group,
				"account_type": account_type,
				"account_currency": currency
			} for account_name, parent_account, is_group, account_type, currency in accounts])

	return test_objects

def get_inventory_account(company, warehouse=None):
	account = None
	if warehouse:
		account = get_warehouse_account(frappe.get_doc("Warehouse", warehouse))
	else:
		account = get_company_default_inventory_account(company)

	return account

def create_account(**kwargs):
	account = frappe.db.get_value("Account", filters={"account_name": kwargs.get("account_name"), "company": kwargs.get("company")})
	if account:
		return account
	else:
		account = frappe.get_doc(dict(
			doctype = "Account",
			account_name = kwargs.get('account_name'),
			account_type = kwargs.get('account_type'),
			parent_account = kwargs.get('parent_account'),
			company = kwargs.get('company'),
			account_currency = kwargs.get('account_currency')
		))

		account.save()
		return account.name
