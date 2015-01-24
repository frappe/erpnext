# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt

import frappe
import unittest
from frappe.exceptions import ValidationError

test_records = frappe.get_test_records('Fixed Asset Account')

class TestFixedAssetAccount(unittest.TestCase):
	def clean_db(self):
		frappe.db.sql("""delete from `tabAccumulated Depreciation` where
			parent = '_Test Fixed Asset Name 1'""")

		frappe.db.sql("""delete from `tabAccumulated Depreciation` where
			parent = '_Test Fixed Asset Name 2'""")

		frappe.db.sql("""delete from `tabFixed Asset Account` where 
			fixed_asset_name='_Test Fixed Asset Name 1'""")

		frappe.db.sql("""delete from `tabFixed Asset Account` where 
			fixed_asset_name='_Test Fixed Asset Name 2'""")

		frappe.db.sql("""delete from `tabAccumulated Depreciation` where
			parent = '_Test Fixed Asset Name 3'""")

		frappe.db.sql("""delete from `tabFixed Asset Account` where 
			fixed_asset_name='_Test Fixed Asset Name 3'""")

	def test_fixed_asset_account_carried_forward(self):	
		self.clean_db()
		account = frappe.copy_doc(test_records[0])
		account.insert()
		self.assertRaises(ValidationError, account.post_journal_entry)
		account = frappe.copy_doc(test_records[2])
		account.insert()

	def test_fixed_asset_account_purchased(self):
		account = frappe.copy_doc(test_records[1])
		account.insert()
		je_name = account.post_journal_entry()
		je = frappe.get_doc("Journal Entry", je_name)
		self.assertTrue("_Test Fixed Asset Account" in [d.account for d in je.accounts])

