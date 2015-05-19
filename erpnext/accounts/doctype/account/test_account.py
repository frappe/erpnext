# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def _make_test_records(verbose):
	from frappe.test_runner import make_test_objects

	accounts = [
		# [account_name, parent_account, is_group]
		["_Test Account Bank Account", "Bank Accounts", 0, "Bank"],

		["_Test Account Stock Expenses", "Direct Expenses", 1, None],
		["_Test Account Shipping Charges", "_Test Account Stock Expenses", 0, "Chargeable"],
		["_Test Account Customs Duty", "_Test Account Stock Expenses", 0, "Tax"],
		["_Test Account Insurance Charges", "_Test Account Stock Expenses", 0, "Chargeable"],
		["_Test Account Stock Adjustment", "_Test Account Stock Expenses", 0, "Stock Adjustment"],


		["_Test Account Tax Assets", "Current Assets", 1, None],
		["_Test Account VAT", "_Test Account Tax Assets", 0, "Tax"],
		["_Test Account Service Tax", "_Test Account Tax Assets", 0, "Tax"],

		["_Test Account Reserves and Surplus", "Current Liabilities", 0, None],

		["_Test Account Cost for Goods Sold", "Expenses", 0, None],
		["_Test Account Excise Duty", "_Test Account Tax Assets", 0, "Tax"],
		["_Test Account Education Cess", "_Test Account Tax Assets", 0, "Tax"],
		["_Test Account S&H Education Cess", "_Test Account Tax Assets", 0, "Tax"],
		["_Test Account CST", "Direct Expenses", 0, "Tax"],
		["_Test Account Discount", "Direct Expenses", 0, None],
		["_Test Write Off", "Indirect Expenses", 0, None],

		# related to Account Inventory Integration
		["_Test Account Stock In Hand", "Current Assets", 0, None],
		["_Test Account Fixed Assets", "Current Assets", 0, None],

		# Receivable / Payable Account
		["_Test Receivable", "Current Assets", 0, "Receivable"],
		["_Test Payable", "Current Liabilities", 0, "Payable"],
	]

	for company, abbr in [["_Test Company", "_TC"], ["_Test Company 1", "_TC1"]]:
		test_objects = make_test_objects("Account", [{
				"doctype": "Account",
				"account_name": account_name,
				"parent_account": parent_account + " - " + abbr,
				"company": company,
				"is_group": is_group,
				"account_type": account_type
			} for account_name, parent_account, is_group, account_type in accounts])

	return test_objects
