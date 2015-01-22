# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt

import frappe
import unittest

test_records = frappe.get_test_records('Fixed Asset Sale')

class TestFixedAssetSale(unittest.TestCase):
	def setup_defaults_in_company(self):
		self.setup_depreciation_expense_account()
		self.setup_accumulated_depreciation_account()
		company = frappe.get_doc("Company", "_Test Company")
		company.default_depreciation_method = "Straight Line"	
		company.default_depreciation_expense_account = "_Test Expense Account"
		company.default_accumulated_depreciation_account = "_Test Accumulated Depreciation Account"
		company.save()

	def setup_depreciation_expense_account(self):
		account = frappe.new_doc("Account")
		account.parent_account = "_Test Expense Account"
		account.account_type = "Expense Account"
		account.company = "_Test Company"
		account.account_name = "_Test Depreciation Expense Account"
		account.group_or_ledger = "Ledger"
		account.insert()

	def setup_accumulated_depreciation_account(self)
		account = frappe.new_doc("Account")
		account.parent_account = "_Test Asset Account"
		account.account_type = "Fixed Asset"
		account.company = "_Test Company"
		account.account_name = "_Test Accumulated Depreciation Account"
		account.group_or_ledger = "Ledger"
		account.insert()
		

	def setup_fixed_asset_account(self):
		account = frappe.get_doc("Fixed Asset Account", "_Test Fixed Asset Name 1")
		if not account:
			account = frappe.new_doc("Fixed Asset Account")
			account.fixed_asset_name = "_Test Fixed Asset Name 1"
			account.fixed_asset_account = "_Test Fixed Asset Account"
			account.company = "_Test Company"
			account.depreciation_rate = 5.00
			account.purchase_date = "2012-10-01"
			previous = account.append("depreciation")
			previous.fiscal_year = "_Test Fiscal Year 2012"
			previous.total_accumulated_depreciation = 623.28
			account.insert()
	

	def sell_carried_over_fixed_asset(self):
		self.setup_defaults_in_company()
		self.setup_fixed_asset_account()

		sale = frappe.new_doc("Fixed Asset Sale")
		sale.company = "_Test Company"
		sale.posting_date = "2014-01-01"
		sale.fixed_asset_account = "Test Fixed Asset Name 1"
		sale.sales_amount = 5000
		sale.sold_to = "_Test Supplier 1"
		sale.insert()
		self.assertTrue(sale.asset_purchase_cost == 25000)
		self.assertTrue(sale.accumulated_depreciation >= 924 and sale.accumulated_depreciation <= 945)
		sale.submit()
		je_name = sale.post_journal_entry()
		je = frappe.get_doc("Journal Entry", je_name)
		self.assertTrue("_Test Fixed Asset Account" in [d.account for d in je.accounts])		
		
