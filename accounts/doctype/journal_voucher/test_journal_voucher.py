# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


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