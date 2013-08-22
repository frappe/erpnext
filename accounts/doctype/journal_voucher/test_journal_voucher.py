# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt


from __future__ import unicode_literals
import unittest
import webnotes

class TestJournalVoucher(unittest.TestCase):
	def test_journal_voucher_with_against_jv(self):
		jv_invoice = webnotes.bean(copy=test_records[2])
		jv_invoice.insert()
		jv_invoice.submit()
		
		self.assertTrue(not webnotes.conn.sql("""select name from `tabJournal Voucher Detail`
			where against_jv=%s""", jv_invoice.doc.name))
		
		jv_payment = webnotes.bean(copy=test_records[0])
		jv_payment.doclist[1].against_jv = jv_invoice.doc.name
		jv_payment.insert()
		jv_payment.submit()
		
		self.assertTrue(webnotes.conn.sql("""select name from `tabJournal Voucher Detail`
			where against_jv=%s""", jv_invoice.doc.name))
			
		self.assertTrue(webnotes.conn.sql("""select name from `tabJournal Voucher Detail`
			where against_jv=%s and credit=400""", jv_invoice.doc.name))
		
		# cancel jv_invoice
		jv_invoice.cancel()
		
		self.assertTrue(not webnotes.conn.sql("""select name from `tabJournal Voucher Detail`
			where against_jv=%s""", jv_invoice.doc.name))
			
	def test_budget(self):
		from accounts.utils import BudgetError
		webnotes.conn.set_value("Company", "_Test Company", "monthly_bgt_flag", "Stop")
		
		jv1 = webnotes.bean(copy=test_records[0])
		jv1.doc.posting_date = "2013-02-12"
		jv1.doclist[2].account = "_Test Account Cost for Goods Sold - _TC"
		jv1.doclist[2].cost_center = "_Test Cost Center - _TC"
		jv1.doclist[2].debit = 20000.0
		jv1.doclist[1].credit = 20000.0
		jv1.insert()
		
		self.assertRaises(BudgetError, jv1.submit)


test_records = [
	[{
		"company": "_Test Company", 
		"doctype": "Journal Voucher", 
		"fiscal_year": "_Test Fiscal Year 2013", 
		"naming_series": "_T-Journal Voucher-",
		"posting_date": "2013-02-14", 
		"user_remark": "test",
		"voucher_type": "Bank Voucher",
		"cheque_no": "33",
		"cheque_date": "2013-02-14"
	}, 
	{
		"account": "_Test Customer - _TC", 
		"doctype": "Journal Voucher Detail", 
		"credit": 400.0,
		"debit": 0.0,
		"parentfield": "entries"
	}, 
	{
		"account": "_Test Account Bank Account - _TC", 
		"doctype": "Journal Voucher Detail", 
		"debit": 400.0,
		"credit": 0.0,
		"parentfield": "entries"
	}],
	[{
		"company": "_Test Company", 
		"doctype": "Journal Voucher", 
		"fiscal_year": "_Test Fiscal Year 2013", 
		"naming_series": "_T-Journal Voucher-",
		"posting_date": "2013-02-14", 
		"user_remark": "test",
		"voucher_type": "Bank Voucher",
		"cheque_no": "33",
		"cheque_date": "2013-02-14"
	}, 
	{
		"account": "_Test Supplier - _TC", 
		"doctype": "Journal Voucher Detail", 
		"credit": 0.0,
		"debit": 400.0,
		"parentfield": "entries"
	}, 
	{
		"account": "_Test Account Bank Account - _TC", 
		"doctype": "Journal Voucher Detail", 
		"debit": 0.0,
		"credit": 400.0,
		"parentfield": "entries"
	}],
	[{
		"company": "_Test Company", 
		"doctype": "Journal Voucher", 
		"fiscal_year": "_Test Fiscal Year 2013", 
		"naming_series": "_T-Journal Voucher-",
		"posting_date": "2013-02-14", 
		"user_remark": "test",
		"voucher_type": "Bank Voucher",
		"cheque_no": "33",
		"cheque_date": "2013-02-14"
	}, 
	{
		"account": "_Test Customer - _TC", 
		"doctype": "Journal Voucher Detail", 
		"credit": 0.0,
		"debit": 400.0,
		"parentfield": "entries"
	}, 
	{
		"account": "Sales - _TC", 
		"doctype": "Journal Voucher Detail", 
		"credit": 400.0,
		"debit": 0.0,
		"parentfield": "entries",
		"cost_center": "_Test Cost Center - _TC"
	}],
]