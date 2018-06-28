# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, unittest
from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry

class TestGLEntry(unittest.TestCase):
	def test_round_off_entry(self):
		frappe.db.set_value("Company", "_Test Company", "round_off_account", "_Test Write Off - _TC")
		frappe.db.set_value("Company", "_Test Company", "round_off_cost_center", "_Test Cost Center - _TC")

		jv = make_journal_entry("_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC", 100, "_Test Cost Center - _TC", submit=False)

		jv.get("accounts")[0].debit = 100.01
		jv.flags.ignore_validate = True
		jv.submit()

		round_off_entry = frappe.db.sql("""select name from `tabGL Entry`
			where voucher_type='Journal Entry' and voucher_no = %s
			and account='_Test Write Off - _TC' and cost_center='_Test Cost Center - _TC'
			and debit = 0 and credit = '.01'""", jv.name)

		self.assertTrue(round_off_entry)

	def test_allow_cost_center_in_entry_of_bs_account(self):
		account_settings = frappe.get_single('Account Settings')
		# set Account Settings
		if not cint(account_settings.allow_cost_center_in_entry_of_bs_account):
			frappe.set_value('Account Settings', 'Account Settings', 'allow_cost_center_in_entry_of_bs_account', 1)

		jv = make_journal_entry("_Test Cash - _TC",
			"_Test Bank - _TC", 100, "_Test Cost Center - _TC", submit=True)

		# reset Account Settings
		frappe.set_value('Account Settings', 'Account Settings', 'allow_cost_center_in_entry_of_bs_account', 0)

		cc_in_bs_account = frappe.db.sql("""select name from `tabGL Entry`
			where voucher_type='Journal Entry' and voucher_no = %s
			and account='_Test Bank - _TC' and cost_center='_Test Cost Center - _TC'
			""", jv.name)

		self.assertTrue(cc_in_bs_account)

