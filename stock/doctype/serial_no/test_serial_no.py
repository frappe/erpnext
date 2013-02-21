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
from webnotes.tests import insert_test_data

company = webnotes.conn.get_default("company")

class TestSerialNo(unittest.TestCase):
	def setUp(self):
		webnotes.conn.begin()
		self.insert_test_data()

	def tearDown(self):
		# print "Message Log:", "\n--\n".join(webnotes.message_log)
		# print "Debug Log:", "\n--\n".join(webnotes.debug_log)
		webnotes.conn.rollback()
		
	def test_serialized_stock_entry(self):
		data = [["2012-01-01", "01:00", "10001", 400, 400],
			["2012-01-01", "03:00", "10002", 500, 700],
			["2012-01-01", "04:00", "10003", 700, 700],
			["2012-01-01", "05:00", "10004", 1200, 800],
			["2012-01-01", "05:00", "10005", 800, 800],
			["2012-01-01", "02:00", "10006", 1200, 800],
			["2012-01-01", "06:00", "10007", 1500, 900]]
		for d in data:
			webnotes.bean([{
				"doctype": "Serial No",
				"item_code": "Nebula 8",
				"warehouse": "Default Warehouse", 
				"status": "In Store",
				"sle_exists": 0,
				"purchase_date": d[0],
				"purchase_time": d[1],
				"serial_no": d[2],
				"purchase_rate": d[3],
				"company": company,
			}]).insert()
			
		for d in data:
			res = webnotes.conn.sql("""select valuation_rate from `tabStock Ledger Entry`
				where posting_date=%s and posting_time=%s and actual_qty=1 and serial_no=%s""",
				(d[0], d[1], d[2]))
			self.assertEquals(res[0][0], d[4])
		
		print "deleted"
		webnotes.delete_doc("Serial No", "10002")
		
		test_data = [["10001", 400, 400],
			["10003", 700, 766.666667],
			["10004", 1200, 875],
			["10005", 800, 860],
			["10006", 1200, 800],
			["10007", 1500, 966.666667]]
		
		for d in test_data:
			res = webnotes.conn.sql("""select valuation_rate from `tabStock Ledger Entry`
				where actual_qty=1 and serial_no=%s""", (d[0],))
			self.assertEquals(res[0][0], d[2])
	
	def insert_test_data(self):
		# create default warehouse
		if not webnotes.conn.exists("Warehouse", "Default Warehouse"):
			webnotes.insert({"doctype": "Warehouse", 
				"warehouse_name": "Default Warehouse",
				"warehouse_type": "Stores"})

		# create UOM: Nos.
		if not webnotes.conn.exists("UOM", "Nos"):
			webnotes.insert({"doctype": "UOM", "uom_name": "Nos"})
			
		# create item groups and items
		insert_test_data("Item Group", 
			sort_fn=lambda ig: (ig[0].get('parent_item_group'), ig[0].get('name')))
		
		insert_test_data("Item")