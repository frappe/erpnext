# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt

import frappe
import unittest
from frappe import ValidationError

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
	

	def test_sell_a_carried_over_fixed_asset(self):
		print "Testing Sale of a Fixed Asset"
		self.setup_defaults_in_company()
		sale = frappe.copy_doc(test_records[0])
		from erpnext.accounts.doctype.fixed_asset_account.depreciation_report \
			import get_written_down_when_selling_fixed_asset
		sale.accumulated_depreciation = get_written_down_when_selling_fixed_asset(\
				sale.fixed_asset_account,\
				sale.posting_date,\
				sale.company,\
				sale.sales_amount)
		self.assertTrue(sale.accumulated_depreciation == 1250)
		sale.difference = float(sale.asset_purchase_cost) - \
				float(sale.accumulated_depreciation) - \
				float(sale.sales_amount)
		sale.insert()
		sale.submit()
		je_name = sale.post_journal_entry()
		self.assertTrue("_Test Account Fixed Assets - _TC" in [d.account for d in je_name.accounts])	

	def test_sell_already_sold_fixed_asset(self):
		print "Testing Already Sold Fixed Asset"
		sale = frappe.copy_doc(test_records[3])
		from erpnext.accounts.doctype.fixed_asset_account.depreciation_report \
			import get_written_down_when_selling_fixed_asset
		self.assertRaises(ValidationError, get_written_down_when_selling_fixed_asset, \
				sale.fixed_asset_account,\
				sale.posting_date,\
				sale.company,\
				sale.sales_amount)
			
		

