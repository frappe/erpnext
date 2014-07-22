# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def _make_test_records(verbose):
	from frappe.test_runner import make_test_objects
		
	accounts = [
		# [account_name, parent_account, group_or_ledger]
		["_Test Account Bank Account", "Bank Accounts", "Ledger", "Bank"],
		
		["_Test Account Stock Expenses", "Direct Expenses", "Group", None],
		["_Test Account Shipping Charges", "_Test Account Stock Expenses", "Ledger", "Chargeable"],
		["_Test Account Customs Duty", "_Test Account Stock Expenses", "Ledger", "Tax"],
		["_Test Account Insurance Charges", "_Test Account Stock Expenses", "Ledger", "Chargeable"],
		
		
		["_Test Account Tax Assets", "Current Assets", "Group", None],
		["_Test Account VAT", "_Test Account Tax Assets", "Ledger", "Tax"],
		["_Test Account Service Tax", "_Test Account Tax Assets", "Ledger", "Tax"],
		
		["_Test Account Reserves and Surplus", "Current Liabilities", "Ledger", None],

		["_Test Account Cost for Goods Sold", "Expenses", "Ledger", None],
		["_Test Account Excise Duty", "_Test Account Tax Assets", "Ledger", "Tax"],
		["_Test Account Education Cess", "_Test Account Tax Assets", "Ledger", "Tax"],
		["_Test Account S&H Education Cess", "_Test Account Tax Assets", "Ledger", "Tax"],
		["_Test Account CST", "Direct Expenses", "Ledger", "Tax"],
		["_Test Account Discount", "Direct Expenses", "Ledger", None],
		
		# related to Account Inventory Integration
		["_Test Account Stock In Hand", "Current Assets", "Ledger", None],
		["_Test Account Fixed Assets", "Current Assets", "Ledger", None],
	]

	for company, abbr in [["_Test Company", "_TC"], ["_Test Company 1", "_TC1"]]:
		test_objects = make_test_objects("Account", [{
				"doctype": "Account",
				"account_name": account_name,
				"parent_account": parent_account + " - " + abbr,
				"company": company,
				"group_or_ledger": group_or_ledger,
				"account_type": account_type
			} for account_name, parent_account, group_or_ledger, account_type in accounts])
	
	return test_objects