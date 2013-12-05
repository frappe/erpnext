# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from __future__ import unicode_literals
import unittest
import webnotes

class TestJournalVoucher(unittest.TestCase):
	def test_journal_voucher_with_against_jv(self):
		self.clear_account_balance()
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
	
	def test_jv_against_stock_account(self):
		from stock.doctype.purchase_receipt.test_purchase_receipt import set_perpetual_inventory
		set_perpetual_inventory()
		
		jv = webnotes.bean(copy=test_records[0])
		jv.doclist[1].account = "_Test Warehouse - _TC"
		jv.insert()
		
		from accounts.general_ledger import StockAccountInvalidTransaction
		self.assertRaises(StockAccountInvalidTransaction, jv.submit)

		set_perpetual_inventory(0)
			
	def test_monthly_budget_crossed_ignore(self):
		webnotes.conn.set_value("Company", "_Test Company", "monthly_bgt_flag", "Ignore")
		self.clear_account_balance()
		
		jv = webnotes.bean(copy=test_records[0])
		jv.doclist[2].account = "_Test Account Cost for Goods Sold - _TC"
		jv.doclist[2].cost_center = "_Test Cost Center - _TC"
		jv.doclist[2].debit = 20000.0
		jv.doclist[1].credit = 20000.0
		jv.insert()
		jv.submit()
		self.assertTrue(webnotes.conn.get_value("GL Entry", 
			{"voucher_type": "Journal Voucher", "voucher_no": jv.doc.name}))
			
	def test_monthly_budget_crossed_stop(self):
		from accounts.utils import BudgetError
		webnotes.conn.set_value("Company", "_Test Company", "monthly_bgt_flag", "Stop")
		self.clear_account_balance()
		
		jv = webnotes.bean(copy=test_records[0])
		jv.doclist[2].account = "_Test Account Cost for Goods Sold - _TC"
		jv.doclist[2].cost_center = "_Test Cost Center - _TC"
		jv.doclist[2].debit = 20000.0
		jv.doclist[1].credit = 20000.0
		jv.insert()
		
		self.assertRaises(BudgetError, jv.submit)
		
		webnotes.conn.set_value("Company", "_Test Company", "monthly_bgt_flag", "Ignore")
		
	def test_yearly_budget_crossed_stop(self):
		from accounts.utils import BudgetError
		self.clear_account_balance()
		self.test_monthly_budget_crossed_ignore()
		
		webnotes.conn.set_value("Company", "_Test Company", "yearly_bgt_flag", "Stop")
		
		jv = webnotes.bean(copy=test_records[0])
		jv.doc.posting_date = "2013-08-12"
		jv.doclist[2].account = "_Test Account Cost for Goods Sold - _TC"
		jv.doclist[2].cost_center = "_Test Cost Center - _TC"
		jv.doclist[2].debit = 150000.0
		jv.doclist[1].credit = 150000.0
		jv.insert()
		
		self.assertRaises(BudgetError, jv.submit)
		
		webnotes.conn.set_value("Company", "_Test Company", "yearly_bgt_flag", "Ignore")
		
	def test_monthly_budget_on_cancellation(self):
		from accounts.utils import BudgetError
		webnotes.conn.set_value("Company", "_Test Company", "monthly_bgt_flag", "Stop")
		self.clear_account_balance()
		
		jv = webnotes.bean(copy=test_records[0])
		jv.doclist[1].account = "_Test Account Cost for Goods Sold - _TC"
		jv.doclist[1].cost_center = "_Test Cost Center - _TC"
		jv.doclist[1].credit = 30000.0
		jv.doclist[2].debit = 30000.0
		jv.submit()
		
		self.assertTrue(webnotes.conn.get_value("GL Entry", 
			{"voucher_type": "Journal Voucher", "voucher_no": jv.doc.name}))
		
		jv1 = webnotes.bean(copy=test_records[0])
		jv1.doclist[2].account = "_Test Account Cost for Goods Sold - _TC"
		jv1.doclist[2].cost_center = "_Test Cost Center - _TC"
		jv1.doclist[2].debit = 40000.0
		jv1.doclist[1].credit = 40000.0
		jv1.submit()
		
		self.assertTrue(webnotes.conn.get_value("GL Entry", 
			{"voucher_type": "Journal Voucher", "voucher_no": jv1.doc.name}))
		
		self.assertRaises(BudgetError, jv.cancel)
		
		webnotes.conn.set_value("Company", "_Test Company", "monthly_bgt_flag", "Ignore")
		
	def clear_account_balance(self):
		webnotes.conn.sql("""delete from `tabGL Entry`""")
		

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