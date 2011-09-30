import unittest

import webnotes
import webnotes.profile
webnotes.user = webnotes.profile.Profile()


from webnotes.model.doc import Document
from webnotes.model.code import get_obj
from webnotes.utils import cstr, flt
from webnotes.model.doclist import getlist
sql = webnotes.conn.sql

from sandbox.testdata.masters import *
from sandbox.testdata import stock_entry
#----------------------------------------------------------


class TestStockEntry(unittest.TestCase):
	#===========================================================================
	def assertDoc(self, lst):
		"""assert all values"""
		for d in lst:
			cl, vl = [], []
			for k in d.keys():
				if k!='doctype':
					cl.append('%s=%s' % (k, '%s'))
					vl.append(d[k])

			self.assertTrue(sql("select name from `tab%s` where %s limit 1" % (d['doctype'], ' and '.join(cl)), vl))
			
	#===========================================================================
	def assertCount(self, lst):
		"""assert all values"""
		for d in lst:
			cl, vl = [], []
			for k in d[0].keys():
				if k!='doctype':
					cl.append('%s=%s' % (k, '%s'))
					vl.append(d[0][k])

			self.assertTrue(sql("select count(name) from `tab%s` where %s limit 1" % (d[0]['doctype'], ' and '.join(cl)), vl)[0][0] == d[1])
		
	#===========================================================================
	def setUp(self):
		print "====================================="
		webnotes.conn.begin()		
		create_master_records()
		print 'Master Data Created'
		
	#===========================================================================
	# Purpose: Material Receipt
	#===========================================================================
	def test_mr_onsubmit(self):
		print "Test Case: Stock Entry submission"
		self.save_stock_entry('Material Receipt')

		mr = get_obj('Stock Entry', stock_entry.mr[0].name, with_children=1)
		self.submit_stock_entry(mr)
		
		# stock ledger entry
		print "Checking stock ledger entry........."
		self.assertDoc(self.get_expected_sle('mr_submit'))
		
		# bin qty
		print "Checking Bin qty........."
		self.assertDoc([{'doctype':'Bin', 'actual_qty':10, 'item_code':'it', 'warehouse':'wh1'}])
		
		# serial no
		self.assertCount([[{'doctype': 'Serial No', 'item_code': 'it', 'warehouse': 'wh1', 'status': 'In Store', 'docstatus': 0}, 10]])

		
	#===========================================================================
	def test_mr_oncancel(self):
		print "Test Case: Stock Entry Cancellation"
		self.save_stock_entry('Material Receipt')
		
		mr = get_obj('Stock Entry', stock_entry.mr[0].name, with_children=1)
		self.cancel_stock_entry(mr)
		
		# stock ledger entry
		print "Checking stock ledger entry........."
		self.assertDoc(self.get_expected_sle('mr_cancel'))
		
		# bin qty
		print "Checking Bin qty........."
		self.assertDoc([{'doctype':'Bin', 'actual_qty':0, 'item_code':'it', 'warehouse':'wh1'}])
		
		# serial no
		self.assertCount([[{'doctype': 'Serial No', 'item_code': 'it', 'warehouse': '', 'status': 'Not in Use', 'docstatus': 2}, 10]])
		
	#===========================================================================
	# Purpose: Material Transafer
	#===========================================================================
	def test_mtn_onsubmit(self):
		print "Test Case: Stock Entry submission"
		
		self.save_stock_entry('Material Receipt')
		mr = get_obj('Stock Entry', stock_entry.mr[0].name, with_children=1)
		mr = self.submit_stock_entry(mr)
		
		self.save_stock_entry('Material Transfer')
		mtn = get_obj('Stock Entry', stock_entry.mtn[0].name, with_children=1)
		tn = self.submit_stock_entry(mtn)
		
		# stock ledger entry
		print "Checking stock ledger entry........."
		self.assertDoc(self.get_expected_sle('mtn_submit'))
		
		# bin qty
		print "Checking Bin qty........."
		self.assertDoc([
			{'doctype':'Bin', 'actual_qty':5, 'item_code':'it', 'warehouse':'wh1'},
			{'doctype':'Bin', 'actual_qty':5, 'item_code':'it', 'warehouse':'wh2'}
		])
		
		# serial no		
		self.assertCount([
			[{'doctype': 'Serial No', 'item_code': 'it', 'warehouse': 'wh1', 'status': 'In Store', 'docstatus': 0}, 5], 
			[{'doctype': 'Serial No', 'item_code': 'it', 'warehouse': 'wh2', 'status': 'In Store', 'docstatus': 0}, 5]
		])
		
	#===========================================================================
	def test_mtn_oncancel(self):
		print "Test Case: Stock Entry Cancellation"
		
		self.save_stock_entry('Material Receipt')
		mr = get_obj('Stock Entry', stock_entry.mr[0].name, with_children=1)
		mr = self.submit_stock_entry(mr)
		
		self.save_stock_entry('Material Transfer')
		mtn = get_obj('Stock Entry', stock_entry.mtn[0].name, with_children=1)
		self.cancel_stock_entry(mtn)
		
		# stock ledger entry
		print "Checking stock ledger entry........."
		self.assertDoc(self.get_expected_sle('mtn_cancel'))
		
		# bin qty
		print "Checking Bin qty........."
		self.assertDoc([
			{'doctype':'Bin', 'actual_qty':10, 'item_code':'it', 'warehouse':'wh1'},
			{'doctype':'Bin', 'actual_qty':0, 'item_code':'it', 'warehouse':'wh2'}
		])
		
		# serial no
		self.assertCount([[{'doctype': 'Serial No', 'item_code': 'it', 'warehouse': 'wh1', 'status': 'In Store', 'docstatus': 0}, 10]])

	#===========================================================================
	def save_stock_entry(self, t):
		if t == 'Material Receipt':
			data = stock_entry.mr
		elif t == 'Material Transfer':
			data = stock_entry.mtn
			
		for each in data:
			each.save(1)

		for t in data[1:]:
			sql("update `tabStock Entry Detail` set parent = '%s' where name = '%s'" % (data[0].name, t.name))
		print "Stock Entry Created"
		
		
	#===========================================================================
	def submit_stock_entry(self, ste):
		ste.validate()
		ste.on_submit()
		
		ste.doc.docstatus = 1
		ste.doc.save()

		print "Stock Entry Submitted"
		return ste
			
	#===========================================================================
	def cancel_stock_entry(self, ste):
		ste = self.submit_stock_entry(ste)
		
		ste.on_cancel()
		
		ste.doc.cancel_reason = "testing"
		ste.doc.docstatus = 2
		ste.doc.save()
		
		print "Stock Entry Cancelled"
		return ste
		
	#===========================================================================
	def tearDown(self):
		webnotes.conn.rollback()


	# Expected Result Set
	#===================================================================================================
	def get_expected_sle(self, action):
		expected_sle = {
			'mr_submit': [{
							'doctype': 'Stock Ledger Entry',
							'item_code':'it',
							'warehouse':'wh1', 
							'voucher_type': 'Stock Entry',
							'voucher_no': stock_entry.mr[0].name,
							'actual_qty': 10,
							'bin_aqat': 10,
							'valuation_rate': 100,
							'is_cancelled': 'No'
						}],
			'mr_cancel': [{
							'doctype': 'Stock Ledger Entry', 
							'item_code':'it',
							'warehouse':'wh1',
							'voucher_type': 'Stock Entry',
							'voucher_no': stock_entry.mr[0].name,
							'actual_qty': 10,
							'bin_aqat': 10,
							'valuation_rate': 100,
							'is_cancelled': 'Yes'
						},{
							'doctype': 'Stock Ledger Entry', 
							'item_code':'it',
							'warehouse':'wh1',
							'voucher_type': 'Stock Entry',
							'voucher_no': stock_entry.mr[0].name,
							'actual_qty': -10,
							'ifnull(bin_aqat, 0)': 0,
							'ifnull(valuation_rate, 0)': 0,
							"ifnull(is_cancelled, 'No')": 'Yes'
						}],
			'mtn_submit': [{
							'doctype': 'Stock Ledger Entry',
							'item_code':'it',
							'warehouse':'wh1',
							'voucher_type': 'Stock Entry',
							'voucher_no': stock_entry.mtn[0].name,
							'actual_qty': -5,
							'bin_aqat': 5,
							'valuation_rate': 100,
							'is_cancelled': 'No'
						}, {
							'doctype': 'Stock Ledger Entry',
							'item_code':'it',
							'warehouse':'wh2',
							'voucher_type': 'Stock Entry',
							'voucher_no': stock_entry.mtn[0].name,
							'actual_qty': 5,
							'bin_aqat': 5,
							'valuation_rate': 100,
							'is_cancelled': 'No'
						}],
			'mtn_cancel': [{
							'doctype': 'Stock Ledger Entry',
							'item_code':'it',
							'warehouse':'wh1',
							'voucher_type': 'Stock Entry',
							'voucher_no': stock_entry.mtn[0].name,
							'actual_qty': -5,
							'bin_aqat': 5,
							'is_cancelled': 'Yes'
						}, {
							'doctype': 'Stock Ledger Entry',
							'item_code':'it',
							'warehouse':'wh2',
							'voucher_type': 'Stock Entry',
							'voucher_no': stock_entry.mtn[0].name,
							'actual_qty': 5,
							'bin_aqat': 5,
							'valuation_rate': 100,
							'is_cancelled': 'Yes'
						}, {
							'doctype': 'Stock Ledger Entry',
							'item_code':'it',
							'warehouse':'wh1',
							'voucher_type': 'Stock Entry',
							'voucher_no': stock_entry.mtn[0].name,
							'actual_qty': 5,
							'is_cancelled': 'Yes'
						}, {
							'doctype': 'Stock Ledger Entry',
							'item_code':'it',
							'warehouse':'wh2',
							'voucher_type': 'Stock Entry',
							'voucher_no': stock_entry.mtn[0].name,
							'actual_qty': -5,
							'is_cancelled': 'Yes'
						}]
		}
		
		return expected_sle[action]
