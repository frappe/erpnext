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
from webnotes.utils import flt
import json

company = webnotes.conn.get_default("company")

class TestStockReconciliation(unittest.TestCase):
	def setUp(self):
		webnotes.conn.begin()
		self.insert_test_data()

	def tearDown(self):
		# print "Message Log:", "\n--\n".join(webnotes.message_log)
		# print "Debug Log:", "\n--\n".join(webnotes.debug_log)
		webnotes.conn.rollback()
		
	def test_reco_for_fifo(self):
		# [[qty, valuation_rate, posting_date, 
		#		posting_time, expected_stock_value, bin_qty, bin_valuation]]
		input_data = [
			[50, 1000, "2012-12-26", "12:00", 50000, 45, 48000], 
			[5, 1000, "2012-12-26", "12:00", 5000, 0, 0], 
			[15, 1000, "2012-12-26", "12:00", 15000, 10, 12000], 
			[25, 900, "2012-12-26", "12:00", 22500, 20, 22500], 
			[20, 500, "2012-12-26", "12:00", 10000, 15, 18000], 
			[50, 1000, "2013-01-01", "12:00", 50000, 65, 68000], 
			[5, 1000, "2013-01-01", "12:00", 5000, 20, 23000],
			["", 1000, "2012-12-26", "12:05", 15000, 10, 12000],
			[20, "", "2012-12-26", "12:05", 16000, 15, 18000],
			[10, 2000, "2012-12-26", "12:10", 20000, 5, 6000],
			[1, 1000, "2012-12-01", "00:00", 1000, 11, 13200],
			[0, "", "2012-12-26", "12:10", 0, -5, 0]
		]
			
		for d in input_data:
			self.insert_existing_sle("FIFO")
			
			self.submit_stock_reconciliation(d[0], d[1], d[2], d[3])
		
			res = webnotes.conn.sql("""select stock_value from `tabStock Ledger Entry`
				where item_code = 'Android Jack D' and warehouse = 'Default Warehouse'
				and posting_date = %s and posting_time = %s order by name desc limit 1""", 
				(d[2], d[3]))
				
			self.assertEqual(res and flt(res[0][0]) or 0, d[4])
			
			bin = webnotes.conn.sql("""select actual_qty, stock_value from `tabBin`
				where item_code = 'Android Jack D' and warehouse = 'Default Warehouse'""")
			
			self.assertEqual(bin and [flt(bin[0][0]), flt(bin[0][1])] or [], [d[5], d[6]])
			
			
			self.tearDown()
			self.setUp()
					
		
	def test_reco_for_moving_average(self):
		# [[qty, valuation_rate, posting_date, 
		#		posting_time, expected_stock_value, bin_qty, bin_valuation]]
		input_data = [
			[50, 1000, "2012-12-26", "12:00", 50000, 45, 48000], 
			[5, 1000, "2012-12-26", "12:00", 5000, 0, 0], 
			[15, 1000, "2012-12-26", "12:00", 15000, 10, 12000], 
			[25, 900, "2012-12-26", "12:00", 22500, 20, 22500], 
			[20, 500, "2012-12-26", "12:00", 10000, 15, 18000], 
			[50, 1000, "2013-01-01", "12:00", 50000, 65, 68000], 
			[5, 1000, "2013-01-01", "12:00", 5000, 20, 23000],
			["", 1000, "2012-12-26", "12:05", 15000, 10, 12000],
			[20, "", "2012-12-26", "12:05", 18000, 15, 18000],
			[10, 2000, "2012-12-26", "12:10", 20000, 5, 6000],
			[1, 1000, "2012-12-01", "00:00", 1000, 11, 13200],
			[0, "", "2012-12-26", "12:10", 0, -5, 0]
			
		]
		
		for d in input_data:
			self.insert_existing_sle("Moving Average")
			
			self.submit_stock_reconciliation(d[0], d[1], d[2], d[3])
		
			res = webnotes.conn.sql("""select stock_value from `tabStock Ledger Entry`
				where item_code = 'Android Jack D' and warehouse = 'Default Warehouse'
				and posting_date = %s and posting_time = %s order by name desc limit 1""", 
				(d[2], d[3]))
				
			self.assertEqual(res and flt(res[0][0], 4) or 0, d[4])
			
			bin = webnotes.conn.sql("""select actual_qty, stock_value from `tabBin`
				where item_code = 'Android Jack D' and warehouse = 'Default Warehouse'""")
			
			self.assertEqual(bin and [flt(bin[0][0]), flt(bin[0][1], 4)] or [], 
				[flt(d[5]), flt(d[6])])
						
			self.tearDown()
			self.setUp()
			
	def submit_stock_reconciliation(self, qty, rate, posting_date, posting_time):
		return webnotes.bean([{
			"doctype": "Stock Reconciliation",
			"name": "RECO-001",
			"__islocal": 1,
			"posting_date": posting_date,
			"posting_time": posting_time,
			"reconciliation_json": json.dumps([
				["Item Code", "Warehouse", "Quantity", "Valuation Rate"],
				["Android Jack D", "Default Warehouse", qty, rate]
			]),
		}]).submit()
		
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
		
	def insert_existing_sle(self, valuation_method):
		webnotes.conn.set_value("Item", "Android Jack D", "valuation_method", valuation_method)
		webnotes.conn.set_default("allow_negative_stock", 1)
		
		existing_ledgers = [
			{
				"doctype": "Stock Ledger Entry", "__islocal": 1,
				"voucher_type": "Stock Entry", "voucher_no": "TEST",
				"item_code": "Android Jack D", "warehouse": "Default Warehouse",
				"posting_date": "2012-12-12", "posting_time": "01:00",
				"actual_qty": 20, "incoming_rate": 1000, "company": company
			},
			{
				"doctype": "Stock Ledger Entry", "__islocal": 1,
				"voucher_type": "Stock Entry", "voucher_no": "TEST",
				"item_code": "Android Jack D", "warehouse": "Default Warehouse",
				"posting_date": "2012-12-15", "posting_time": "02:00",
				"actual_qty": 10, "incoming_rate": 700, "company": company
			},
			{
				"doctype": "Stock Ledger Entry", "__islocal": 1,
				"voucher_type": "Stock Entry", "voucher_no": "TEST",
				"item_code": "Android Jack D", "warehouse": "Default Warehouse",
				"posting_date": "2012-12-25", "posting_time": "03:00",
				"actual_qty": -15, "company": company
			},
			{
				"doctype": "Stock Ledger Entry", "__islocal": 1,
				"voucher_type": "Stock Entry", "voucher_no": "TEST",
				"item_code": "Android Jack D", "warehouse": "Default Warehouse",
				"posting_date": "2012-12-31", "posting_time": "08:00",
				"actual_qty": -20, "company": company
			},
			{
				"doctype": "Stock Ledger Entry", "__islocal": 1,
				"voucher_type": "Stock Entry", "voucher_no": "TEST",
				"item_code": "Android Jack D", "warehouse": "Default Warehouse",
				"posting_date": "2013-01-05", "posting_time": "07:00",
				"actual_qty": 15, "incoming_rate": 1200, "company": company
			},
		]
		
		webnotes.get_obj("Stock Ledger").update_stock(existing_ledgers)