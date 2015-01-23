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
		company.default_depreciation_expense_account = "_Test Depreciation Expense Account - _TC"
		company.default_accumulated_depreciation_account = "_Test Accumulated Depreciation Account - _TC"
		company.save()

	def setup_depreciation_expense_account(self):
		frappe.db.sql("""delete from `tabAccount` where 
			account_name like '%Depreciation Exp%'""")		
		account = frappe.copy_doc(test_records[1])
		account.insert()

	def setup_accumulated_depreciation_account(self):
		frappe.db.sql("""delete from `tabAccount` where 
			account_name like '%Accumulated Depr%'""")		
		account = frappe.copy_doc(test_records[2])
		account.insert()
	

	def test_sell_carried_over_fixed_asset(self):
		print "Testing Sale of a Fixed Asset"
		self.setup_defaults_in_company()
		sale = frappe.copy_doc(test_records[0])
		sale.insert()
		self.assertTrue(sale.asset_purchase_cost == 25000)
		self.assertTrue(sale.accumulated_depreciation >= 924 and sale.accumulated_depreciation <= 945)
		sale.submit()
		je_name = sale.post_journal_entry()
		je = frappe.get_doc("Journal Entry", je_name)
		self.assertTrue("_Test Fixed Asset Account" in [d.account for d in je.accounts])		
		
