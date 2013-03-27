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

test_records = []

# from webnotes.model.doc import Document
# from webnotes.model.code import get_obj
# from webnotes.utils import cstr, flt
# sql = webnotes.conn.sql
# 
# class TestInternalReco(unittest.TestCase):
# 	def setUp(self):
# 		webnotes.conn.begin()
# 		
# 		comp1.save(1)
# 		cust1.save(1)
# 		bank1.save(1)
# 		rv1.save(1)
# 		rv_gle.save(1)
# 
# 
# 		for t in jv1: t.save(1)
# 		for t in jv1[1:]:
# 			sql("update `tabJournal Voucher Detail` set parent = '%s' where name = '%s'" % (jv1[0].name, t.name))
# 			
# 		ir[0].save()
# 		for t in ir[1:]:
# 			t.save(1)
# 			sql("update `tabPayment to Invoice Matching Tool Detail` set voucher_no = '%s', voucher_detail_no = '%s' where parent = 'Payment to Invoice Matching Tool'" % (jv1[0].name, jv1[1].name))
# 		
# 		
# 		sql("update `tabGL Entry` set voucher_no = %s, against_voucher = %s where voucher_no = 'rv1'", (rv1.name, rv1.name))
# 		sql("update `tabSingles` set value = %s where doctype = 'Payment to Invoice Matching Tool' and field = 'voucher_no'", rv1.name)
# 		
# 		
# 		self.ir = get_obj('Payment to Invoice Matching Tool', with_children=1)		
# 		self.ir.reconcile()
# 		
# 	#===========================
# 	def test_jv(self):
# 		"""
# 			Test whether JV has benn properly splitted and against doc has been updated
# 		"""
# 		amt_against_doc = [[cstr(d[0]), flt(d[1]), flt(d[2])]for d in sql("select against_invoice, debit, credit from `tabJournal Voucher Detail` where parent = %s and account = 'cust1 - c1'", jv1[0].name)]
# 		self.assertTrue(amt_against_doc == [[rv1.name, 0, 100.0], ['', 0, 400.0]])
# 
# 	#============================		
# 	def test_gl_entry(self):
# 		"""
# 			Check proper gl entry has been made
# 		"""
# 		gle = [[cstr(d[0]), flt(d[1])] for d in sql("select against_voucher, sum(credit) - sum(debit) from `tabGL Entry` where voucher_no = %s and account = 'cust1 - c1' and ifnull(is_cancelled, 'No') = 'No' group by against_voucher", jv1[0].name)]
# 
# 		self.assertTrue([rv1.name, 100.0] in gle)
# 		self.assertTrue(['', 400.0] in gle)
# 		
# 	#============================
# 	def test_outstanding(self):
# 		"""
# 			Check whether Outstanding amount has been properly updated in RV
# 		"""
# 		amt = sql("select outstanding_amount from `tabSales Invoice` where name = '%s'" % rv1.name)[0][0]
# 		self.assertTrue(amt == 0)
# 		
# 	#============================
# 	def tearDown(self):
# 		webnotes.conn.rollback()
# 	
# 
# 
# 
# # test data
# #---------------
# rv1 = Document(fielddata={
# 		'doctype':'Sales Invoice',
# 		'docstatus':1,
# 		'debit_to':'cust1 - c1',
# 		'grand_total': 100,
# 		'outstanding_amount': 100,
# 		'name': 'rv1'
# 	})
# 	
# jv1 = [Document(fielddata={
# 		'doctype':'Journal Voucher',
# 		'docstatus':1,
# 		'cheque_no': '163567',
# 		'docstatus':1,
# 		'company': 'comp1',
# 		'posting_date' : '2011-05-02',
# 		'remark': 'test data',
# 		'fiscal_year': '2011-2012',
# 		'total_debit': 500,
# 		'total_credit': 500
# 	}),
# 	Document(fielddata = {
# 		'parenttype':'Journal Voucher',
# 		'parentfield':'entries',
# 		'doctype':'Journal Voucher Detail',
# 		'account' : 'cust1 - c1',
# 		'credit':500,
# 		'debit' : 0,
# 		'docstatus':1
# 	}),
# 	Document(fielddata = {
# 		'parenttype':'Journal Voucher',
# 		'parentfield':'entries',
# 		'doctype':'Journal Voucher Detail',
# 		'account' : 'bank1 - c1',
# 		'credit':0,
# 		'debit' : 500,
# 		'docstatus':1
# 	})]
# 	
# ir = [Document(fielddata = {
# 		'doctype':'Payment to Invoice Matching Tool',
# 		'name' : 'Payment to Invoice Matching Tool',
# 		'account':'cust1 - c1',
# 		'voucher_type' : 'Sales Invoice',
# 		'voucher_no': 'rv1'
# 	}),
# 	Document(fielddata = {
# 		'parenttype':'Payment to Invoice Matching Tool',
# 		'parentfield':'ir_payment_details',
# 		'doctype':'Payment to Invoice Matching Tool Detail',
# 		'parent': 'Payment to Invoice Matching Tool',
# 		'voucher_no': 'jv1',
# 		'name' : '123112',
# 		'voucher_detail_no' : 'jvd1',
# 		'selected' : 1,
# 		'amt_due' : 500,
# 		'amt_to_be_reconciled':100
# 	})]
# 	
# cust1 = Document(fielddata={
# 		'doctype':'Account',
# 		'docstatus':0,
# 		'account_name' : 'cust1',
# 		'debit_or_credit': 'Debit',
# 		'company' : 'comp1',
# 		'lft': 1,
# 		'rgt': 2
# 	})
# 	
# bank1 = Document(fielddata={
# 		'doctype':'Account',
# 		'docstatus':0,
# 		'account_name' : 'bank1',
# 		'debit_or_credit': 'Debit',
# 		'company' : 'comp1',
# 		'lft': 3,
# 		'rgt': 4
# 	})	
# 	
# comp1 = Document(fielddata={
# 		'doctype':'Company',
# 		'abbr': 'c1',
# 		'company_name' : 'comp1',
# 		'name': 'comp1'
# 	})
# 	
# rv_gle = Document(fielddata={
# 		'doctype':'GL Entry',
# 		'account': 'cust1 - c1',
# 		'company' : 'comp1',
# 		'voucher_no': 'rv1',
# 		'against_voucher': 'rv1',
# 		'against_voucher_type': 'Sales Invoice',
# 		'voucher_type' : 'Sales Invoice',
# 		'debit': 100,
# 		'credit': 0
# 	})
