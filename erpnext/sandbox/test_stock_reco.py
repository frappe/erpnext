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
from sandbox.testdata.sle_data import sle, bin
from sandbox.testdata.stock_reco import *
#----------------------------------------------------------


class TestStockEntry(unittest.TestCase):
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
	def setUp(self):
		print "====================================="
		webnotes.conn.begin()		
		create_master_records()
		print 'Master Data Created'
		
		for d in sle:
			d.save(1)
		print "Existing SLE created"
		
		bin.save(1)
		
		sreco.save(1)
		print "Stock Reco saved"
		
	#===========================================================================
	def test_diff_in_both(self):
		reco = get_obj('Stock Reconciliation', sreco.name)
		reco.doc.docstatus = 1
		reco.doc.save()
		reco.validate()
		reco.on_submit()
		print "Stock Reco submitted"
		
		print "Checking stock ledger entry........."
		self.assertDoc(self.get_expected_sle('diff_in_both'))

	#===========================================================================
	def tearDown(self):
		webnotes.conn.rollback()
		
	# Expected Result Set
	#===================================================================================================
	def get_expected_sle(self, action):
		expected_sle = {
			'diff_in_both': [{
							'doctype': 'Stock Ledger Entry',
							'item_code':'it',
							'warehouse':'wh1', 
							'voucher_type': 'Stock Reconciliation',
							'voucher_no': sreco.name,
							'actual_qty': 15,
							'bin_aqat': 20,
							'valuation_rate': 150,
							#'stock_value': 3000,
							'is_cancelled': 'No'
						},{
							'doctype': 'Stock Ledger Entry',
							'posting_date': '2011-09-10',
							'posting_time': '15:00',
							'item_code': 'it',
							'warehouse': 'wh1',
							'actual_qty': 20,
							'incoming_rate': 200,
							'bin_aqat': 40,
							'valuation_rate': 175,
							#'stock_value': 4500,
							'is_cancelled': 'No'
						}
						]
		}
		return expected_sle[action]
