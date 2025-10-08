# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import unittest

import frappe
from frappe.test_runner import make_test_records
from frappe.tests.utils import change_settings
from frappe.utils import nowdate

from erpnext.accounts.doctype.account.account import (
	InvalidAccountMergeError,
	RootNotEditable,
	merge_account,
	update_account_number,
)
from erpnext.stock import get_company_default_inventory_account, get_warehouse_account

test_dependencies = ["Company"]


class TestAccount(unittest.TestCase):
	def tearDown(self):
		frappe.local.flags.allow_unverified_charts = False
		frappe.db.rollback()

	def test_delete_account_with_children(self):
		create_account(
			account_name="Parent Account",
			is_group=1,
			parent_account="Application of Funds (Assets) - _TC",
			company="_Test Company",
		)

		create_account(
			account_name="Child Account 1", parent_account="Parent Account - _TC", company="_Test Company"
		)

		create_account(
			account_name="Child Account 2", parent_account="Parent Account - _TC", company="_Test Company"
		)

		self.assertRaises(frappe.ValidationError, frappe.delete_doc, "Account", "Parent Account - _TC")

		frappe.delete_doc("Account", "Child Account 1 - _TC")
		frappe.delete_doc("Account", "Child Account 2 - _TC")

	def test_rename_account(self):
		if frappe.db.exists("Account", "1211-11-4 - 6 - - Debtors 1 - Test - - _TC"):
			frappe.delete_doc("Account", "1211-11-4 - 6 - - Debtors 1 - Test - - _TC")

		if not frappe.db.exists("Account", "1210 - Debtors - _TC"):
			acc = frappe.new_doc("Account")
			acc.account_name = "Debtors"
			acc.parent_account = "Accounts Receivable - _TC"
			acc.account_number = "1210"
			acc.company = "_Test Company"
			acc.insert(ignore_permissions=True)

			account_number, account_name = frappe.db.get_value(
				"Account", "1210 - Debtors - _TC", ["account_number", "account_name"]
			)
			self.assertEqual(account_number, "1210")
			self.assertEqual(account_name, "Debtors")

		new_account_number = "1211-11-4 - 6 - "
		new_account_name = "Debtors 1 - Test - "

		update_account_number("1210 - Debtors - _TC", new_account_name, new_account_number)

		new_acc = frappe.db.get_value(
			"Account",
			"1211-11-4 - 6 - - Debtors 1 - Test - - _TC",
			["account_name", "account_number"],
			as_dict=1,
		)

		self.assertEqual(new_acc.account_name, "Debtors 1 - Test -")
		self.assertEqual(new_acc.account_number, "1211-11-4 - 6 -")

		frappe.delete_doc("Account", "1211-11-4 - 6 - Debtors 1 - Test - - _TC")

	def test_merge_account(self):
		create_account(
			account_name="Current Assets",
			is_group=1,
			parent_account="Application of Funds (Assets) - _TC",
			company="_Test Company",
		)

		create_account(
			account_name="Securities and Deposits",
			is_group=1,
			parent_account="Current Assets - _TC",
			company="_Test Company",
		)

		create_account(
			account_name="Earnest Money",
			parent_account="Securities and Deposits - _TC",
			company="_Test Company",
		)

		create_account(
			account_name="Cash In Hand",
			is_group=1,
			parent_account="Current Assets - _TC",
			company="_Test Company",
		)

		create_account(
			account_name="Receivable INR",
			parent_account="Current Assets - _TC",
			company="_Test Company",
			account_currency="INR",
		)

		create_account(
			account_name="Receivable USD",
			parent_account="Current Assets - _TC",
			company="_Test Company",
			account_currency="USD",
		)

		parent = frappe.db.get_value("Account", "Earnest Money - _TC", "parent_account")

		self.assertEqual(parent, "Securities and Deposits - _TC")

		merge_account("Securities and Deposits - _TC", "Cash In Hand - _TC")

		parent = frappe.db.get_value("Account", "Earnest Money - _TC", "parent_account")

		# Parent account of the child account changes after merging
		self.assertEqual(parent, "Cash In Hand - _TC")

		# Old account doesn't exist after merging
		self.assertFalse(frappe.db.exists("Account", "Securities and Deposits - _TC"))

		# Raise error as is_group property doesn't match
		self.assertRaises(
			InvalidAccountMergeError,
			merge_account,
			"Current Assets - _TC",
			"Accumulated Depreciation - _TC",
		)

		# Raise error as root_type property doesn't match
		self.assertRaises(
			InvalidAccountMergeError,
			merge_account,
			"Capital Stock - _TC",
			"Softwares - _TC",
		)

		# Raise error as currency doesn't match
		self.assertRaises(
			InvalidAccountMergeError,
			merge_account,
			"Receivable INR - _TC",
			"Receivable USD - _TC",
		)

	def test_account_sync(self):
		frappe.local.flags.pop("ignore_root_company_validation", None)

		acc = frappe.new_doc("Account")
		acc.account_name = "Test Sync Account"
		acc.parent_account = "Temporary Accounts - _TC3"
		acc.company = "_Test Company 3"
		acc.insert(ignore_permissions=True)

		acc_tc_4 = frappe.db.get_value(
			"Account", {"account_name": "Test Sync Account", "company": "_Test Company 4"}
		)
		acc_tc_5 = frappe.db.get_value(
			"Account", {"account_name": "Test Sync Account", "company": "_Test Company 5"}
		)
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
		acc.insert(ignore_permissions=True)

		# Rename account in parent company
		update_account_number(acc.name, "Test Rename Sync Account", "1234")

		# Check if renamed in children
		self.assertTrue(
			frappe.db.exists(
				"Account",
				{
					"account_name": "Test Rename Sync Account",
					"company": "_Test Company 4",
					"account_number": "1234",
				},
			)
		)
		self.assertTrue(
			frappe.db.exists(
				"Account",
				{
					"account_name": "Test Rename Sync Account",
					"company": "_Test Company 5",
					"account_number": "1234",
				},
			)
		)

		frappe.delete_doc("Account", "1234 - Test Rename Sync Account - _TC3")
		frappe.delete_doc("Account", "1234 - Test Rename Sync Account - _TC4")
		frappe.delete_doc("Account", "1234 - Test Rename Sync Account - _TC5")

	def test_account_currency_sync(self):
		"""
		In a parent->child company setup, child should inherit parent account currency if explicitly specified.
		"""

		make_test_records("Company")

		frappe.local.flags.pop("ignore_root_company_validation", None)

		def create_bank_account():
			acc = frappe.new_doc("Account")
			acc.account_name = "_Test Bank JPY"

			acc.parent_account = "Temporary Accounts - _TC6"
			acc.company = "_Test Company 6"
			return acc

		acc = create_bank_account()
		# Explicitly set currency
		acc.account_currency = "JPY"
		acc.insert(ignore_permissions=True)
		self.assertTrue(
			frappe.db.exists(
				{
					"doctype": "Account",
					"account_name": "_Test Bank JPY",
					"account_currency": "JPY",
					"company": "_Test Company 7",
				}
			)
		)

		frappe.delete_doc("Account", "_Test Bank JPY - _TC6")
		frappe.delete_doc("Account", "_Test Bank JPY - _TC7")

		acc = create_bank_account()
		# default currency is used
		acc.insert(ignore_permissions=True)
		self.assertTrue(
			frappe.db.exists(
				{
					"doctype": "Account",
					"account_name": "_Test Bank JPY",
					"account_currency": "USD",
					"company": "_Test Company 7",
				}
			)
		)

		frappe.delete_doc("Account", "_Test Bank JPY - _TC6")
		frappe.delete_doc("Account", "_Test Bank JPY - _TC7")

	def test_child_company_account_rename_sync(self):
		frappe.local.flags.pop("ignore_root_company_validation", None)

		acc = frappe.new_doc("Account")
		acc.account_name = "Test Group Account"
		acc.parent_account = "Temporary Accounts - _TC3"
		acc.is_group = 1
		acc.company = "_Test Company 3"
		acc.insert(ignore_permissions=True)

		self.assertTrue(
			frappe.db.exists("Account", {"account_name": "Test Group Account", "company": "_Test Company 4"})
		)
		self.assertTrue(
			frappe.db.exists("Account", {"account_name": "Test Group Account", "company": "_Test Company 5"})
		)

		# Try renaming child company account
		acc_tc_5 = frappe.db.get_value(
			"Account", {"account_name": "Test Group Account", "company": "_Test Company 5"}
		)
		self.assertRaises(frappe.ValidationError, update_account_number, acc_tc_5, "Test Modified Account")

		# Rename child company account with allow_account_creation_against_child_company enabled
		frappe.db.set_value("Company", "_Test Company 5", "allow_account_creation_against_child_company", 1)

		update_account_number(acc_tc_5, "Test Modified Account")
		self.assertTrue(
			frappe.db.exists(
				"Account", {"name": "Test Modified Account - _TC5", "company": "_Test Company 5"}
			)
		)

		frappe.db.set_value("Company", "_Test Company 5", "allow_account_creation_against_child_company", 0)

		to_delete = [
			"Test Group Account - _TC3",
			"Test Group Account - _TC4",
			"Test Modified Account - _TC5",
		]
		for doc in to_delete:
			frappe.delete_doc("Account", doc)

	def test_validate_account_currency(self):
		from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry

		if not frappe.db.get_value("Account", "Test Currency Account - _TC"):
			acc = frappe.new_doc("Account")
			acc.account_name = "Test Currency Account"
			acc.parent_account = "Tax Assets - _TC"
			acc.company = "_Test Company"
			acc.insert(ignore_permissions=True)
		else:
			acc = frappe.get_doc("Account", "Test Currency Account - _TC")

		self.assertEqual(acc.account_currency, "INR")

		# Make a JV against this account
		make_journal_entry("Test Currency Account - _TC", "Miscellaneous Expenses - _TC", 100, submit=True)

		acc.account_currency = "USD"
		self.assertRaises(frappe.ValidationError, acc.save)

	def test_account_balance(self):
		from erpnext.accounts.utils import get_balance_on

		if not frappe.db.exists("Account", "Test Percent Account %5 - _TC"):
			acc = frappe.new_doc("Account")
			acc.account_name = "Test Percent Account %5"
			acc.parent_account = "Tax Assets - _TC"
			acc.company = "_Test Company"
			acc.insert(ignore_permissions=True)

		balance = get_balance_on(account="Test Percent Account %5 - _TC", date=nowdate())
		self.assertEqual(balance, 0)

	def test_allow_unverified_chart_TC_ACC_167(self):
		company = make_company(company_name="Test Company")
		frappe.local.flags.allow_unverified_charts = True
		if frappe.db.exists("Account", "Test Account - TC"):
			frappe.delete_doc("Account", "Test Account - TC", force=1)
		account = frappe.new_doc("Account")
		account.account_name = "Test Account"
		account.company = company.name
		account.parent_account = "Cash In Hand - TC"
		account.insert(ignore_permissions=True)
		self.assertEqual(account.parent_account, "Cash In Hand - TC")

	def test_validate_parent_child_account_type_TC_ACC_168(self):
		make_company(company_name="_Test Company")

		parent_account = create_account(
			account_name="Expenses Test",
			is_group=1,
			parent_account="Expenses - _TC",
			company="_Test Company",
			do_not_save=True,
		)
		parent_account.account_type = "Direct Expense"
		parent_account.save(ignore_permissions=True)
		self.assertEqual(parent_account.account_type, "Direct Expense")
		acc = frappe.new_doc("Account")
		acc.account_name = "Test Account"
		acc.parent_account = parent_account.name
		acc.company = "_Test Company"
		acc.account_type = "Direct Expense"
		with self.assertRaises(frappe.ValidationError, msg=f"Only Parent can be of type {acc.account_type}"):
			acc.save(ignore_permissions=True)

	def test_validate_parent_account_not_assign_TC_ACC_169(self):
		make_company(company_name="_Test Company")
		account = frappe.new_doc("Account")
		account.account_name = "Cash In Hand"
		account.parent_account = "Cash In Hand - _TC"
		account.company = "_Test Company"
		account.flags.ignore_if_duplicate = True
		with self.assertRaises(
			frappe.ValidationError,
			msg=f"Account {account.parent_account}: You can not assign itself as parent account",
		):
			account.save(ignore_permissions=True)

	def test_validate_parent_account_is_group_TC_ACC_170(self):
		make_company(company_name="_Test Company")
		account = frappe.new_doc("Account")
		account.account_name = "Test Account"
		account.is_group = 0
		account.parent_account = "Cash - _TC"
		account.company = "_Test Company"
		with self.assertRaises(
			frappe.ValidationError,
			msg=f"Account Test Account - _TC: Parent account {account.parent_account} can not be a ledger",
		):
			account.save(ignore_permissions=True)

	def test_validate_parent_account_for_company_TC_ACC_171(self):
		make_company(company_name="_Test Company")
		account = frappe.new_doc("Account")
		account.account_name = "Test Account"
		account.is_group = 0
		account.parent_account = "Current Assets - _TC1"
		account.company = "_Test Company"
		with self.assertRaises(
			frappe.ValidationError,
			msg=f"Account Test Account - _TC: Parent account {account.parent_account} does not belong to company: _Test Company",
		):
			account.save(ignore_permissions=True)

	def test_set_root_and_report_type_TC_ACC_172(self):
		make_company(company_name="_Test Company")
		account = frappe.get_doc("Account", "Current Assets - _TC")
		account.db_set("root_type", "Income")
		account.db_set("report_type", "Profit and Loss")
		account.save()
		account.reload()
		self.assertEqual(account.root_type, "Asset")
		self.assertEqual(account.report_type, "Balance Sheet")

	def test_validate_receivable_payable_account_type_TC_ACC_173(self):
		from erpnext.buying.doctype.supplier.test_supplier import create_supplier
		from erpnext.stock.doctype.item.test_item import create_item
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		make_company(company_name="_Test Company")
		item_code = "_Test Item"
		supplier = "_Test Supplier"

		create_warehouse(
			warehouse_name="_Test Warehouse - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC", "account": "Cost of Goods Sold - _TC"},
			company="_Test Company",
		)
		create_supplier(supplier_name=supplier, default_currency="INR")
		item = create_item(item_code=item_code, valuation_rate=100)
		pi = frappe.new_doc("Purchase Invoice")
		pi.supplier = supplier
		pi.company = "_Test Company"
		pi.currency = "INR"
		pi.append("items", {"item_code": item.item_code, "qty": 8, "rate": 100})
		pi.save()
		pi.submit()
		account = frappe.get_doc("Account", "Creditors - _TC")
		account.account_type = "Cash"
		account.save()

	def test_validate_root_details_TC_ACC_174(self):
		make_company(company_name="_Test Company")
		account = frappe.get_doc("Account", "Application of Funds (Assets) - _TC")
		account.account_type = "Cash"
		with self.assertRaises(RootNotEditable, msg="Root cannot be edited."):
			account.save(ignore_permissions=True)

	def test_validate_root_account_must_be_group_TC_ACC_175(self):
		make_company(company_name="_Test Company")
		account = frappe.new_doc("Account")
		account.account_name = "Test Account"
		account.company = "_Test Company"
		account.account_type = "Cash"
		with self.assertRaises(
			frappe.ValidationError, msg="The root account Test Account - _TC must be a group"
		):
			account.save(ignore_permissions=True)

	def test_with_child_node_convert_group_to_ledger_TC_ACC_176(self):
		make_company(company_name="_Test Company")
		create_account(
			account_name="Test Parent Account",
			parent_account="Cash In Hand - _TC",
			company="_Test Company",
			account_type="Direct Income",
			is_group=1,
		)
		frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": "Test Child",
				"parent_account": "Test Parent Account - _TC",
				"company": "_Test Company",
			}
		).insert()
		parent_doc = frappe.get_doc("Account", "Test Parent Account - _TC")
		with self.assertRaises(
			frappe.ValidationError, msg="Account with child nodes cannot be converted to ledger"
		):
			parent_doc.convert_group_to_ledger()

	def test_convert_group_to_ledger_with_ledger_exists_TC_ACC_177(self):
		from erpnext.buying.doctype.supplier.test_supplier import create_supplier
		from erpnext.stock.doctype.item.test_item import create_item
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		make_company(company_name="_Test Company")
		item_code = "_Test Item"
		supplier = "_Test Supplier"

		create_warehouse(
			warehouse_name="Test Warehouse - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC", "account": "Cost of Goods Sold - _TC"},
			company="_Test Company",
		)
		create_supplier(supplier_name=supplier, default_currency="INR")
		item = create_item(item_code=item_code, valuation_rate=100)
		pi = frappe.new_doc("Purchase Invoice")
		pi.supplier = supplier
		pi.company = "_Test Company"
		pi.currency = "INR"
		pi.append("items", {"item_code": item.item_code, "qty": 8, "rate": 100})
		pi.save()
		pi.submit()
		account = frappe.get_doc("Account", "Creditors - _TC")
		with self.assertRaises(
			frappe.ValidationError, msg="Account with existing transaction cannot be converted to ledger"
		):
			account.convert_group_to_ledger()

	def test_should_convert_to_ledger_TC_ACC_178(self):
		make_company(company_name="_Test Company")
		account = frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": "Test Convertible Account",
				"is_group": 1,
				"company": "_Test Company",
				"parent_account": "Accounts Receivable - _TC",
				"root_type": "Asset",
			}
		).insert()
		account.convert_group_to_ledger()
		account.reload()
		self.assertEqual(account.is_group, 0)

	@change_settings(
		"Accounts Settings",
		{"delete_linked_ledger_entries": 1},
	)
	def test_validate_group_or_ledger_TC_ACC_179(self):
		make_company(company_name="_Test Company")
		from erpnext.buying.doctype.supplier.test_supplier import create_supplier
		from erpnext.stock.doctype.item.test_item import create_item
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		item_code = "_Test Item"
		supplier = "_Test Supplier"

		create_warehouse(
			warehouse_name="Test Warehouse - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC", "account": "Cost of Goods Sold - _TC"},
			company="_Test Company",
		)
		create_supplier(supplier_name=supplier, default_currency="INR")
		item = create_item(item_code=item_code, valuation_rate=100)
		pi = frappe.new_doc("Purchase Invoice")
		pi.supplier = supplier
		pi.company = "_Test Company"
		pi.currency = "INR"
		pi.append("items", {"item_code": item.item_code, "qty": 8, "rate": 100})
		pi.save()
		pi.submit()
		account = frappe.get_doc("Account", "Creditors - _TC")
		account.is_group = 1
		with self.assertRaises(
			frappe.ValidationError, msg="Account with existing transaction cannot be converted to ledger"
		):
			account.save(ignore_permissions=True)
		pi.cancel()
		pi.delete()
		gl_1 = frappe.get_all("GL Entry", filters={"account": "Creditors - _TC"}, pluck="name")
		if len(gl_1) > 0:
			for gl in gl_1:
				frappe.delete_doc_if_exists("GL Entry", gl, force=1)
		account.reload()
		account.is_group = 1
		with self.assertRaises(
			frappe.ValidationError, msg="Cannot covert to Group because Account Type is selected."
		):
			account.save(ignore_permissions=True)

	def test_validate_frozen_accounts_modifier_TC_ACC_180(self):
		frappe.set_user("Guest")
		make_company(company_name="_Test Company")
		account = frappe.get_doc("Account", "Current Assets - _TC")
		account.freeze_account = "Yes"
		with self.assertRaises(frappe.ValidationError, msg="You are not authorized to set Frozen value"):
			account.save(ignore_permissions=True)
		frappe.set_user("Administrator")

	def test_validate_balance_must_be_credit_TC_ACC_181(self):
		make_company(company_name="_Test Company")
		account = frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": "Test Convertible Account",
				"is_group": 0,
				"company": "_Test Company",
				"parent_account": "Accounts Receivable - _TC",
			}
		).insert()
		journal_entry = frappe.get_doc(
			{
				"doctype": "Journal Entry",
				"voucher_type": "Journal Entry",
				"company": "_Test Company",
				"posting_date": frappe.utils.nowdate(),
				"accounts": [
					{"account": account.name, "debit_in_account_currency": 1000},
					{"account": "Cash - _TC", "credit_in_account_currency": 1000},
				],
			}
		)
		journal_entry.insert()
		journal_entry.submit()
		account.balance_must_be = "Credit"
		with self.assertRaises(
			frappe.ValidationError,
			msg="Account balance already in Debit, you are not allowed to set 'Balance Must Be' as 'Credit'",
		):
			account.save(ignore_permissions=True)

	def test_validate_balance_should_be_credit_TC_ACC_182(self):
		make_company(company_name="_Test Company")
		account = frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": "Test Convertible Account",
				"is_group": 0,
				"company": "_Test Company",
				"parent_account": "Accounts Receivable - _TC",
			}
		).insert()
		journal_entry = frappe.get_doc(
			{
				"doctype": "Journal Entry",
				"voucher_type": "Journal Entry",
				"company": "_Test Company",
				"posting_date": frappe.utils.nowdate(),
				"accounts": [
					{"account": account.name, "credit_in_account_currency": 1000},
					{"account": "Cash - _TC", "debit_in_account_currency": 1000},
				],
			}
		)
		journal_entry.insert()
		journal_entry.submit()
		account.balance_must_be = "Debit"
		with self.assertRaises(
			frappe.ValidationError,
			msg="Account balance already in Credit, you are not allowed to set 'Balance Must Be' as 'Debit'",
		):
			account.save(ignore_permissions=True)

	def test_validate_account_currency_TC_ACC_183(self):
		make_company(company_name="_Test Company")
		from erpnext.buying.doctype.supplier.test_supplier import create_supplier
		from erpnext.stock.doctype.item.test_item import create_item
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		item_code = "_Test Item"
		supplier = "_Test Supplier"

		create_warehouse(
			warehouse_name="Test Warehouse - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC", "account": "Cost of Goods Sold - _TC"},
			company="_Test Company",
		)
		create_supplier(supplier_name=supplier, default_currency="INR")
		item = create_item(item_code=item_code, valuation_rate=100)
		pi = frappe.new_doc("Purchase Invoice")
		pi.supplier = supplier
		pi.company = "_Test Company"
		pi.currency = "INR"
		pi.append("items", {"item_code": item.item_code, "qty": 8, "rate": 100})
		pi.save()
		pi.submit()
		account = frappe.get_doc("Account", pi.credit_to)
		account.account_currency = "USD"
		with self.assertRaises(
			frappe.ValidationError,
			msg="Currency can not be changed after making entries using some other currency",
		):
			account.save(ignore_permissions=True)

	def test_validate_account_number_TC_ACC_184(self):
		make_company(company_name="_Test Company")
		create_account(
			account_name="Test Parent Account",
			parent_account="Cash In Hand - _TC",
			company="_Test Company",
			account_type="Cash",
		)
		parent_account = frappe.get_doc("Account", "Test Parent Account - _TC")
		update_account_number(
			name=parent_account.name, account_name=parent_account.account_name, account_number="12345"
		)
		acc = frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": "Test account 89",
				"is_group": 0,
				"company": "_Test Company",
				"parent_account": "Accounts Receivable - _TC",
				"account_number": "12345",
			}
		)
		with self.assertRaises(
			frappe.ValidationError,
			msg="Account Number 12345 already used in account 12345 - Test Parent Account - _TC",
		):
			acc.save(ignore_permissions=True)

	def test_convert_ledger_to_group_with_ledger_exists_TC_ACC_185(self):
		from erpnext.buying.doctype.supplier.test_supplier import create_supplier
		from erpnext.stock.doctype.item.test_item import create_item
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		make_company(company_name="_Test Company")
		item_code = "_Test Item"
		supplier = "_Test Supplier"

		create_warehouse(
			warehouse_name="Test Warehouse - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC", "account": "Cost of Goods Sold - _TC"},
			company="_Test Company",
		)
		create_supplier(supplier_name=supplier, default_currency="INR")
		item = create_item(item_code=item_code, valuation_rate=100)
		pi = frappe.new_doc("Purchase Invoice")
		pi.supplier = supplier
		pi.company = "_Test Company"
		pi.currency = "INR"
		pi.append("items", {"item_code": item.item_code, "qty": 8, "rate": 100})
		pi.save()
		pi.submit()
		account = frappe.get_doc("Account", "Creditors - _TC")
		with self.assertRaises(
			frappe.ValidationError, msg="Account with existing transaction can not be converted to group"
		):
			account.convert_ledger_to_group()

	def test_check_account_type_convert_ledger_to_group_TC_ACC_186(self):
		make_company(company_name="_Test Company")
		account = frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": "Test account",
				"is_group": 0,
				"company": "_Test Company",
				"account_type": "Cash",
				"parent_account": "Accounts Receivable - _TC",
			}
		)
		with self.assertRaises(
			frappe.ValidationError, msg="Cannot convert to Group because Account Type is selected."
		):
			account.convert_ledger_to_group()

	def test_should_convert_ledger_to_group_TC_ACC_187(self):
		make_company(company_name="_Test Company")
		account = frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": "Test Ledger Account",
				"is_group": 0,
				"company": "_Test Company",
				"parent_account": "Accounts Receivable - _TC",
			}
		).insert()
		account.convert_ledger_to_group()
		account.reload()
		self.assertEqual(account.is_group, 1)

	def test_validate_madantory_TC_ACC_189(self):
		make_company(company_name="_Test Company")
		account = frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": "Test account",
				"is_group": 1,
				"company": "_Test Company",
			}
		)
		with self.assertRaises(frappe.ValidationError, msg="Root Type is mandatory"):
			account.save(ignore_permissions=True)

	def test_check_gle_exists_on_trash_TC_ACC_190(self):
		from erpnext.buying.doctype.supplier.test_supplier import create_supplier
		from erpnext.stock.doctype.item.test_item import create_item
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		make_company(company_name="_Test Company")
		item_code = "_Test Item"
		supplier = "_Test Supplier"

		create_warehouse(
			warehouse_name="Test Warehouse - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC", "account": "Cost of Goods Sold - _TC"},
			company="_Test Company",
		)
		create_supplier(supplier_name=supplier, default_currency="INR")
		item = create_item(item_code=item_code, valuation_rate=100)
		pi = frappe.new_doc("Purchase Invoice")
		pi.supplier = supplier
		pi.company = "_Test Company"
		pi.currency = "INR"
		pi.append("items", {"item_code": item.item_code, "qty": 8, "rate": 100})
		pi.save()
		pi.submit()
		account = frappe.get_doc("Account", "Creditors - _TC")
		with self.assertRaises(
			frappe.ValidationError, msg="Account with existing transaction can not be deleted"
		):
			account.delete()

	def test_get_parent_account_method_TC_ACC_191(self):
		make_company(company_name="_Test Company")
		from erpnext.accounts.doctype.account.account import get_parent_account

		frappe.set_user("Administrator")
		get_parent_account(
			doctype="Account",
			txt="",
			searchfield="name",
			start=0,
			page_len=20,
			filters={"company": "_Test Company"},
		)

	def test_get_account_autoname_company_validation_TC_ACC_192(self):
		from erpnext.accounts.doctype.account.account import get_account_autoname

		make_company(company_name="_Test Company")
		account = frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": "Test account 89",
				"is_group": 1,
				"account_number": "45678",
				"company": "_Test Company",
			}
		)
		with self.assertRaises(frappe.ValidationError, msg="Company None does not exist"):
			get_account_autoname(
				account_number=account.account_number, account_name=account.account_name, company=None
			)

	def test_update_account_number_TC_ACC_193(self):
		frappe.set_user("Administrator")

		# Create parent company if not exists
		if frappe.db.exists("Company", "Test Parent Company"):
			parent = frappe.get_doc("Company", "Test Parent Company")
		else:
			parent = frappe.get_doc(
				{
					"doctype": "Company",
					"company_name": "Test Parent Company",
					"is_group": 1,
					"abbr": "TPC1",
					"default_currency": "INR",
				}
			)
			parent.insert()

		# Create child company if not exists
		if frappe.db.exists("Company", "Test Child Company"):
			company = frappe.get_doc("Company", "Test Child Company")
		else:
			company = frappe.get_doc(
				{
					"doctype": "Company",
					"company_name": "Test Child Company",
					"parent_company": parent.name,
					"abbr": "TCC1",
					"default_currency": "INR",
				}
			)
			company.insert()

		# Create root account if not exists
		if not frappe.db.exists("Account", {"account_name": "root", "company": company.name}):
			root_account = frappe.new_doc("Account")
			root_account.account_name = "root"
			root_account.is_group = 1
			root_account.root_type = "Asset"
			root_account.company = company.name
			root_account.insert(ignore_mandatory=True)
		else:
			root_account = frappe.get_doc("Account", {"account_name": "root", "company": company.name})

		# Create parent account in parent company
		if not frappe.db.exists("Account", {"name": "1210 - Debtors - TPC"}):
			par_acc = frappe.new_doc("Account")
			par_acc.account_name = "Debtors"
			par_acc.account_number = "1210"
			par_acc.is_group = 1
			par_acc.company = parent.name
			par_acc.root_type = "Asset"
			par_acc.insert(ignore_mandatory=True)

		# Create account in child company
		if not frappe.db.exists("Account", {"name": "1210 - Debtors - TCC"}):
			acc = frappe.new_doc("Account")
			acc.account_name = "Debtors"
			acc.parent_account = root_account.name
			acc.account_number = "1210"
			acc.company = company.name
			acc.insert(ignore_permissions=True)

		account_details = frappe.db.get_value(
			"Account", "1210 - Debtors - TCC1", ["account_number", "account_name"]
		)
		self.assertIsNotNone(account_details, "Account '1210 - Debtors - TCC1' not found")
		account_number, account_name = account_details

		self.assertEqual(account_number, "1210")
		self.assertEqual(account_name, "Debtors")

		new_account_number = "1211-11-4 - 6 - "
		new_account_name = "Debtors 1 - Test - "

		msg = "Account Debtors exists in parent company Test Parent Company.Renaming it is only allowed via parent company Test Parent Company, to avoid mismatch.To overrule this, enable 'Allow Account Creation Against Child Company' in company Test Child Company"
		with self.assertRaises(frappe.ValidationError, msg=msg):
			update_account_number(
				name="1210 - Debtors - TCC1", account_name=new_account_name, account_number=new_account_number
			)

	def test_get_coa_TC_ACC_194(self):
		# Setup
		from erpnext.accounts.utils import get_coa

		frappe.set_user("Administrator")
		doctype = "Account"
		parent = "All Accounts"
		chart = "Standard"

		# Execute
		result = get_coa(doctype, parent, chart=chart)

		# Assert
		assert isinstance(result, list)
		for account in result:
			assert account["parent_account"] in [None, "All Accounts"]
		assert len(result) > 0

	def test_validate_existing_bank_account_TC_ACC_195(self):
		# Setup
		from unittest.mock import patch

		from erpnext.accounts.doctype.account.chart_of_accounts.chart_of_accounts import validate_bank_account

		frappe.set_user("Administrator")
		coa = "Standard"
		test_bank_account = "Bank Account 1"

		# get_chart to return a test chart structure
		def mock_get_chart(coa_name):
			return {
				"Assets": {
					"Bank Accounts": {test_bank_account: {"account_number": "12345", "account_type": "Bank"}}
				}
			}

		# Patch the get_chart function
		with patch(
			"erpnext.accounts.doctype.account.chart_of_accounts.chart_of_accounts.get_chart", mock_get_chart
		):
			result = validate_bank_account(coa, test_bank_account)

			# Assert
			assert result is True


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
		["_Test Depreciations", "Expenses", 0, "Depreciation", None],
		["_Test Gain/Loss on Asset Disposal", "Expenses", 0, None, None],
		# Receivable / Payable Account
		["_Test Receivable", "Current Assets", 0, "Receivable", None],
		["_Test Payable", "Current Liabilities", 0, "Payable", None],
		["_Test Receivable USD", "Current Assets", 0, "Receivable", "USD"],
		["_Test Payable USD", "Current Liabilities", 0, "Payable", "USD"],
	]

	for company, abbr in [
		["_Test Company", "_TC"],
		["_Test Company 1", "_TC1"],
		["_Test Company with perpetual inventory", "TCP1"],
	]:
		test_objects = make_test_objects(
			"Account",
			[
				{
					"doctype": "Account",
					"account_name": account_name,
					"parent_account": parent_account + " - " + abbr,
					"company": company,
					"is_group": is_group,
					"account_type": account_type,
					"account_currency": currency,
				}
				for account_name, parent_account, is_group, account_type, currency in accounts
			],
		)

	return test_objects


def make_company(company_name, is_group=False, **kwargs):
	company = frappe._dict()
	if not frappe.db.exists("Company", company_name):
		company = frappe.get_doc(
			dict(
				doctype="Company",
				company_name=company_name,
				company_type="Company",
				default_currency=kwargs.get("default_currency") or "INR",
				country=kwargs.get("country") or "India",
				is_group=is_group,
				parent_company=kwargs.get("parent_company"),
				allow_account_creation_against_child_company=kwargs.get(
					"allow_account_creation_against_child_company", False
				),
			)
		).insert(ignore_permissions=True)
	else:
		company = frappe.get_doc("Company", company_name)
	return company


def get_inventory_account(company, warehouse=None):
	account = None
	if warehouse:
		account = get_warehouse_account(frappe.get_doc("Warehouse", warehouse))
	else:
		account = get_company_default_inventory_account(company)

	return account


def create_account(**kwargs):
	account = frappe.db.get_value(
		"Account", filters={"account_name": kwargs.get("account_name"), "company": kwargs.get("company")}
	)
	if account:
		account = frappe.get_doc("Account", account)
		account.update(
			dict(
				is_group=kwargs.get("is_group", 0),
				parent_account=kwargs.get("parent_account"),
			)
		)
	else:
		account = frappe.get_doc(
			dict(
				doctype="Account",
				is_group=kwargs.get("is_group", 0),
				account_name=kwargs.get("account_name"),
				account_type=kwargs.get("account_type"),
				parent_account=kwargs.get("parent_account"),
				company=kwargs.get("company"),
				account_currency=kwargs.get("account_currency"),
			)
		)

	if kwargs.get("do_not_save"):
		return account
	else:
		account.save()
		return account.name
