import unittest

import webnotes
import webnotes.profile
webnotes.user = webnotes.profile.Profile()


from webnotes.model.doc import Document
from webnotes.model.code import get_obj
from webnotes.utils import cstr, flt
sql = webnotes.conn.sql

from sandbox.testdata.masters import *
from sandbox.testdata import stock_entry
#----------------------------------------------------------

class TestStockEntry(unittest.TestCase):
	def setUp(self):
		print "====================================="
		webnotes.conn.begin()
		
		create_master_records()
		print 'Master Data Created'
		
		for each in stock_entry.mr:
			each.save(1)

		for t in stock_entry.mr[1:]:
			sql("update `tabStock Entry Detail` set parent = '%s' where name = '%s'" % (stock_entry.mr[0].name, t.name))
		print "Stock Entry Created"
		
	
	#===========================================================================
	def test_stock_entry_onsubmit(self):
		print "Test Case: Stock Entry submission"
		self.submit_stock_entry()
		
		expected_sle = (('Stock Entry', stock_entry.mr[0].name, 10, 10, 100, 'No'),)
		self.check_sle(expected_sle)
		
		self.check_bin_qty(10)
		self.check_serial_no('submit', 10)
		
	#===========================================================================
	def test_stock_entry_oncancel(self):
		print "Test Case: Stock Entry Cancellation"
		self.cancel_stock_entry()
		
		expected_sle = (
			('Stock Entry', stock_entry.mr[0].name, 10, 10, 100, 'Yes'), 
			('Stock Entry', stock_entry.mr[0].name, -10, None, None, 'Yes'),
		)
		self.check_sle(expected_sle)
		
		self.check_bin_qty(0)		
		self.check_serial_no('cancel', 10)
		
		
	#===========================================================================
	def submit_stock_entry(self):
		ste1 = get_obj('Stock Entry', stock_entry.mr[0].name, with_children=1)
		ste1.validate()
		ste1.on_submit()
		
		ste1.doc.docstatus = 1
		ste1.doc.save()
		
		print "Stock Entry Submitted"
		
			
	#===========================================================================
	def cancel_stock_entry(self):
		self.submit_stock_entry()
		
		ste1 = get_obj('Stock Entry', stock_entry.mr[0].name, with_children=1)
		ste1.on_cancel()
		
		ste1.doc.cancel_reason = "testing"
		ste1.doc.docstatus = 2
		ste1.doc.save()
		
		print "Stock Entry Cancelled"
		
	#===========================================================================
	def check_sle(self, expected):
		print "Checking stock ledger entry........."
		sle = sql("select voucher_type, voucher_no, actual_qty, bin_aqat, valuation_rate, is_cancelled from `tabStock Ledger Entry` where item_code = 'it' and warehouse = 'wh1'")
		self.assertTrue(sle == expected)

	#===========================================================================
	def check_bin_qty(self, expected_qty):
		print "Checking Bin qty........."
		bin_qty = sql("select actual_qty from tabBin where item_code = 'it' and warehouse = 'wh1'")
		self.assertTrue(bin_qty[0][0] == expected_qty)
		
	#===========================================================================
	def check_serial_no(self, action, cnt):
		print "Checking serial nos........"
		if action == 'submit':
			status, wh, docstatus = 'In Store', 'wh1', 0
		else:
			status, wh, docstatus = 'Not in Use', '', 2

		ser = sql("select count(name) from `tabSerial No` where item_code = 'it' and warehouse = '%s' and status = '%s' and docstatus = %s" % (wh, status, docstatus))

		self.assertTrue(ser[0][0] == cnt)
	
	#===========================================================================
	def tearDown(self):
		webnotes.conn.rollback()
