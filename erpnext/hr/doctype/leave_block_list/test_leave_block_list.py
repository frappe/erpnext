# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes
import unittest

from hr.doctype.leave_block_list.leave_block_list import get_applicable_block_dates

class TestLeaveBlockList(unittest.TestCase):
	def tearDown(self):
		webnotes.session.user = "Administrator"
		
	def test_get_applicable_block_dates(self):
		webnotes.session.user = "test@example.com"
		webnotes.conn.set_value("Department", "_Test Department", "leave_block_list", 
			"_Test Leave Block List")
		self.assertTrue("2013-01-02" in 
			[d.block_date for d in get_applicable_block_dates("2013-01-01", "2013-01-03")])
			
	def test_get_applicable_block_dates_for_allowed_user(self):
		webnotes.session.user = "test1@example.com"
		webnotes.conn.set_value("Department", "_Test Department 1", "leave_block_list", 
			"_Test Leave Block List")
		self.assertEquals([], [d.block_date for d in get_applicable_block_dates("2013-01-01", "2013-01-03")])
	
	def test_get_applicable_block_dates_all_lists(self):
		webnotes.session.user = "test1@example.com"
		webnotes.conn.set_value("Department", "_Test Department 1", "leave_block_list", 
			"_Test Leave Block List")
		self.assertTrue("2013-01-02" in 
			[d.block_date for d in get_applicable_block_dates("2013-01-01", "2013-01-03", all_lists=True)])
		
test_dependencies = ["Employee"]

test_records = [[{
		"doctype":"Leave Block List",
		"leave_block_list_name": "_Test Leave Block List",
		"year": "_Test Fiscal Year 2013",
		"company": "_Test Company"
	}, {
		"doctype": "Leave Block List Date",
		"parent": "_Test Leave Block List",
		"parenttype": "Leave Block List",
		"parentfield": "leave_block_list_dates",
		"block_date": "2013-01-02",
		"reason": "First work day"
	}, {
		"doctype": "Leave Block List Allow",
		"parent": "_Test Leave Block List",
		"parenttype": "Leave Block List",
		"parentfield": "leave_block_list_allowed",
		"allow_user": "test1@example.com",
		}
	]]