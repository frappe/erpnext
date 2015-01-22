# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt

import frappe
import unittest

test_records = frappe.get_test_records('Fixed Asset Account')

class TestFixedAssetAccount(unittest.TestCase):
	
	def test_fixed_asset_account_carried_forward(self):		
		account = frappe.new_doc("Fixed Asset Account")
		account.fixed_asset_name = "Test Fixed Asset Name 1"
		account.fixed_asset_account = "_Test Fixed Asset Account"
		account.company = "_Test Company"
		account.depreciation_rate = 5.00
		account.purchase_date = "2012-10-01"
		previous = account.append("depreciation")
		previous.fiscal_year = "_Test Fiscal Year 2012"
		previous.total_accumulated_depreciation = 623.28
		account.insert()
		self.assertRaises(ValidationError, account.post_journal_entry)

	def test_fixed_asset_account_purchased(self):
		account = frappe.new_doc("Fixed Asset Account")
		account.fixed_asset_name = "Test Fixed Asset Name 2"
		account.fixed_asset_account = "_Test Fixed Asset Account"
		account.company = "_Test Company"
		account.depreciation_rate = 5.00
		account.purchase_date = "2013-10-01"
		account.insert()
		je_name = account.post_journal_entry()
		je = frappe.get_doc("Journal Entry", je_name)
		self.assertTrue("_Test Fixed Asset Account" in [d.account for d in je.accounts])
