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
import json
from accounts.utils import get_fiscal_year
from pprint import pprint

company = webnotes.conn.get_default("company")

class TestStockReconciliation(unittest.TestCase):
	def setUp(self):
		webnotes.conn.begin()
		self.insert_test_data()

	def tearDown(self):
		print "Message Log:", webnotes.message_log
		webnotes.conn.rollback()
		
	def test_reco_for_fifo(self):
		webnotes.conn.set_value("Item", "Android Jack D", "valuation_method", "FIFO")
		self.submit_stock_reconciliation("2012-12-26", "12:05", 50, 1000)
		
		res = webnotes.conn.sql("""select stock_queue from `tabStock Ledger Entry`
			where item_code = 'Android Jack D' and warehouse = 'Default Warehouse' 
			and voucher_no = 'RECO-001'""")
		
		self.assertEqual(res[0][0], [[50, 1000]])
		
	def test_reco_for_moving_average(self):
		webnotes.conn.set_value("Item", "Android Jack D", "valuation_method", "Moving Average")
		
	def submit_stock_reconciliation(self, posting_date, posting_time, qty, rate):
		return webnotes.model_wrapper([{
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
		# create item groups and items
		insert_test_data("Item Group", 
			sort_fn=lambda ig: (ig[0].get('parent_item_group'), ig[0].get('name')))
		insert_test_data("Item")
		
		# create default warehouse
		if not webnotes.conn.exists("Warehouse", "Default Warehouse"):
			webnotes.insert({"doctype": "Warehouse", 
				"warehouse_name": "Default Warehouse",
				"warehouse_type": "Stores"})
				
		# create UOM: Nos.
		if not webnotes.conn.exists("UOM", "Nos"):
			webnotes.insert({"doctype": "UOM", "uom_name": "Nos"})
		
		existing_ledgers = [
			{
				"doctype": "Stock Ledger Entry", "__islocal": 1,
				"voucher_type": "Stock Entry", "voucher_no": "TEST",
				"item_code": "Android Jack D", "warehouse": "Default Warehouse",
				"posting_date": "2012-12-12", "posting_time": "01:00:00",
				"actual_qty": 20, "incoming_rate": 1000, "company": company
			},
			{
				"doctype": "Stock Ledger Entry", "__islocal": 1,
				"voucher_type": "Stock Entry", "voucher_no": "TEST",
				"item_code": "Android Jack D", "warehouse": "Default Warehouse",
				"posting_date": "2012-12-15", "posting_time": "02:00:00",
				"actual_qty": 10, "incoming_rate": 700, "company": company
			},
			{
				"doctype": "Stock Ledger Entry", "__islocal": 1,
				"voucher_type": "Stock Entry", "voucher_no": "TEST",
				"item_code": "Android Jack D", "warehouse": "Default Warehouse",
				"posting_date": "2012-12-25", "posting_time": "03:00:00",
				"actual_qty": -15, "company": company
			},
			{
				"doctype": "Stock Ledger Entry", "__islocal": 1,
				"voucher_type": "Stock Entry", "voucher_no": "TEST",
				"item_code": "Android Jack D", "warehouse": "Default Warehouse",
				"posting_date": "2012-12-31", "posting_time": "08:00:00",
				"actual_qty": -20, "company": company
			},
			{
				"doctype": "Stock Ledger Entry", "__islocal": 1,
				"voucher_type": "Stock Entry", "voucher_no": "TEST",
				"item_code": "Android Jack D", "warehouse": "Default Warehouse",
				"posting_date": "2013-01-05", "posting_time": "07:00:00",
				"actual_qty": 15, "incoming_rate": 1200, "company": company
			},
		]
		
		pprint(webnotes.conn.sql("""select * from `tabBin` where item_code='Android Jack D' 
			and warehouse='Default Warehouse'""", as_dict=1))
		
		webnotes.get_obj("Stock Ledger").update_stock(existing_ledgers)
		
		pprint(webnotes.conn.sql("""select * from `tabBin` where item_code='Android Jack D' 
			and warehouse='Default Warehouse'""", as_dict=1))
			
		