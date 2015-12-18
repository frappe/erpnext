# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, unittest
from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry

class TestGLEntry(unittest.TestCase):
	def test_round_off_entry(self):
		frappe.db.set_value("Organization", "_Test Organization", "round_off_account", "_Test Write Off - _TO")
		frappe.db.set_value("Organization", "_Test Organization", "round_off_cost_center", "_Test Cost Center - _TO")

		jv = make_journal_entry("_Test Account Cost for Goods Sold - _TO",
			"_Test Bank - _TO", 100, "_Test Cost Center - _TO", submit=False)

		jv.get("accounts")[0].debit = 100.01
		jv.flags.ignore_validate = True
		jv.submit()

		round_off_entry = frappe.db.sql("""select name from `tabGL Entry`
			where voucher_type='Journal Entry' and voucher_no = %s
			and account='_Test Write Off - _TO' and cost_center='_Test Cost Center - _TO'
			and debit = 0 and credit = '.01'""", jv.name)

		self.assertTrue(round_off_entry)
