# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from __future__ import unicode_literals
import unittest
import frappe
from erpnext.accounts.doctype.journal_voucher.test_journal_voucher import test_records as jv_records

class TestPeriodClosingVoucher(unittest.TestCase):
	def test_closing_entry(self):
		# clear GL Entries
		frappe.db.sql("""delete from `tabGL Entry`""")
		jv = frappe.copy_doc(jv_records[2])
		jv.insert()
		jv.submit()

		jv1 = frappe.copy_doc(jv_records[0])
		jv1.get("entries")[1].account = "_Test Account Cost for Goods Sold - _TC"
		jv1.get("entries")[1].cost_center = "_Test Cost Center - _TC"
		jv1.get("entries")[1].debit = 600.0
		jv1.get("entries")[0].credit = 600.0
		jv1.insert()
		jv1.submit()

		pcv = frappe.copy_doc(test_records[0])
		pcv.insert()
		pcv.submit()

		gl_entries = frappe.db.sql("""select account, debit, credit
			from `tabGL Entry` where voucher_type='Period Closing Voucher' and voucher_no=%s
			order by account asc, debit asc""", pcv.name, as_dict=1)

		self.assertTrue(gl_entries)

		expected_gl_entries = sorted([
			["_Test Account Reserves and Surplus - _TC", 200.0, 0.0],
			["_Test Account Cost for Goods Sold - _TC", 0.0, 600.0],
			["Sales - _TC", 400.0, 0.0]
		])
		for i, gle in enumerate(gl_entries):
			self.assertEquals(expected_gl_entries[i][0], gle.account)
			self.assertEquals(expected_gl_entries[i][1], gle.debit)
			self.assertEquals(expected_gl_entries[i][2], gle.credit)


test_dependencies = ["Customer", "Cost Center"]
test_records = frappe.get_test_records("Period Closing Voucher")
