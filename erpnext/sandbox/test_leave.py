import unittest

import webnotes
import webnotes.profile
webnotes.user = webnotes.profile.Profile()


from webnotes.model.doc import Document
from webnotes.model.code import get_obj
from webnotes.utils import cstr, flt
from webnotes.model.doclist import getlist
sql = webnotes.conn.sql

from sandbox.testdata import leaves
#----------------------------------------------------------


class TestStockEntry(unittest.TestCase):
	#===========================================================================
	def setUp(self):
		webnotes.conn.begin()
		leaves.emp.save(new = 1, make_autoname = 0)

	def test_leave_bal(self):
		leaves.l_all.save(1)
		leaves.l_app1.save(1)
		leaves.l_app2.save(1)

		la1 = get_obj('Leave Application', leaves.l_app1.name, with_children=1)
		la1.validate()
		la1.doc.docstatus = 1
		la1.doc.save()
		
		self.assertTrue(la1.doc.total_leave_days == 2)
		
		la1.doc.half_day  = 1
		la1.validate()
		la1.doc.save()
		
		self.assertTrue(la1.doc.total_leave_days == .5)

		print "Test case for leave applied no of days"
		
				
		la2 = get_obj('Leave Application', leaves.l_app2.name, with_children=1)
		la2.validate()
		bal = la2.get_leave_balance()
		self.assertTrue(bal, 18)
		print "Test case for leave balance"
		
		
		
		
	def tearDown(self):
		webnotes.conn.rollback()
