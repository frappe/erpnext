# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from __future__ import unicode_literals
import unittest
import frappe
from frappe.utils import flt
from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry

class TestPeriodClosingVoucher(unittest.TestCase):
	def test_closing_entry(self):
		make_journal_entry("_Test Account Bank Account - _TC", "Sales - _TC", 400, 
			"_Test Cost Center - _TC", submit=True)
		
		make_journal_entry("_Test Account Cost for Goods Sold - _TC", 
			"_Test Account Bank Account - _TC", 600, "_Test Cost Center - _TC", submit=True)
			
		profit_or_loss = frappe.db.sql("""select sum(ifnull(t1.debit,0))-sum(ifnull(t1.credit,0)) as balance
			from `tabGL Entry` t1, `tabAccount` t2
			where t1.account = t2.name and ifnull(t2.report_type, '') = 'Profit and Loss'
			and t2.docstatus < 2 and t2.company = '_Test Company'
			and t1.posting_date between '2013-01-01' and '2013-12-31'""")
			
		profit_or_loss = flt(profit_or_loss[0][0]) if profit_or_loss else 0
		
		pcv = self.make_period_closing_voucher()
		
		gle_value = frappe.db.sql("""select ifnull(debit, 0) - ifnull(credit, 0)
			from `tabGL Entry` where voucher_type='Period Closing Voucher' and voucher_no=%s
			and account = '_Test Account Reserves and Surplus - _TC'""", pcv.name)
			
		gle_value = flt(gle_value[0][0]) if gle_value else 0

		self.assertEqual(gle_value, profit_or_loss)
		
	def make_period_closing_voucher(self):
		pcv = frappe.get_doc({
			"doctype": "Period Closing Voucher",
			"closing_account_head": "_Test Account Reserves and Surplus - _TC",
			"company": "_Test Company",
			"fiscal_year": "_Test Fiscal Year 2013",
			"posting_date": "2013-12-31",
			"remarks": "test"
		})
		pcv.insert()
		pcv.submit()
		
		return pcv


test_dependencies = ["Customer", "Cost Center"]
test_records = frappe.get_test_records("Period Closing Voucher")
