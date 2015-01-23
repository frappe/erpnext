# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt

import frappe
import unittest
<<<<<<< HEAD
from frappe.exceptions import ValidationError
=======
>>>>>>> 4cedaef192f522086bcf5f3fc18455d7c0d50e77

test_records = frappe.get_test_records('Fixed Asset Account')

class TestFixedAssetAccount(unittest.TestCase):
	
<<<<<<< HEAD
	def test_fixed_asset_account_carried_forward(self):	
		frappe.db.sql("""delete from `tabFixed Asset Account` where 
			fixed_asset_name='_Test Fixed Asset Name 1'""")
		account = frappe.copy_doc(test_records[0])
		account.insert()
		self.assertRaises(ValidationError, account.post_journal_entry)

	def test_fixed_asset_account_purchased(self):
		frappe.db.sql("""delete from `tabFixed Asset Account` where 
			fixed_asset_name='_Test Fixed Asset Name 2'""")
		account = frappe.copy_doc(test_records[1])
		account.insert()
		je_name = account.post_journal_entry()
		je = frappe.get_doc("Journal Entry", je_name)
		self.assertTrue("_Test Fixed Asset Account" in [d.account for d in je.accounts])
=======
	def test_fixed_asset_account(self):
		account = frappe.copy_doc(test_records[0])
		account.insert()
		je_name = account.post_journal_entry()
		je = frappe.get_doc("Journal Entry", je_name)
		self.assertTrue("Fixed Assets" in [d.account for d in je.accounts])
>>>>>>> 4cedaef192f522086bcf5f3fc18455d7c0d50e77
