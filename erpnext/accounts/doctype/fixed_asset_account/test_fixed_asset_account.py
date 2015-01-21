# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt

import frappe
import unittest

test_records = frappe.get_test_records('Fixed Asset Account')

class TestFixedAssetAccount(unittest.TestCase):
	
	def test_fixed_asset_account(self):
		account = frappe.copy_doc(test_records[0])
		account.insert()
		je_name = account.post_journal_entry()
		je = frappe.get_doc("Journal Entry", je_name)
		self.assertTrue("Fixed Assets" in [d.account for d in je.accounts])
