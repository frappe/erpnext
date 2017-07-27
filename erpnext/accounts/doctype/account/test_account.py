# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from erpnext.stock import get_warehouse_account, get_company_default_inventory_account


def _make_test_records(verbose):
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

		# related to Account Inventory Integration
		["_Test Account Stock In Hand", "Current Assets", 0, None, None],
		
		# fixed asset depreciation
		["_Test Fixed Asset", "Current Assets", 0, "Fixed Asset", None],
		["_Test Accumulated Depreciations", "Current Assets", 0, None, None],
		["_Test Depreciations", "Expenses", 0, None, None],
		["_Test Gain/Loss on Asset Disposal", "Expenses", 0, None, None],

		# Receivable / Payable Account
		["_Test Receivable", "Current Assets", 0, "Receivable", None],
		["_Test Payable", "Current Liabilities", 0, "Payable", None],
		["_Test Receivable USD", "Current Assets", 0, "Receivable", "USD"],
		["_Test Payable USD", "Current Liabilities", 0, "Payable", "USD"]
	]

	for company, abbr in [["_Test Company", "_TC"], ["_Test Company 1", "_TC1"]]:
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
		account = get_warehouse_account(warehouse, company)
	else:
		account = get_company_default_inventory_account(company)

	return account

def create_account(**kwargs):
	account = frappe.get_doc(dict(
		doctype = "Account",
		account_name = kwargs.get('account_name'),
		account_type = kwargs.get('account_type'),
		parent_account = kwargs.get('parent_account'),
		company = kwargs.get('company')
	))
	
	account.save()
	return account.name
