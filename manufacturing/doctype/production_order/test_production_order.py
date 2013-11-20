# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from __future__ import unicode_literals
import unittest
import webnotes
from stock.doctype.purchase_receipt.test_purchase_receipt import set_perpetual_inventory
from manufacturing.doctype.production_order.production_order import make_stock_entry


class TestProductionOrder(unittest.TestCase):
	def test_planned_qty(self):
		set_perpetual_inventory(0)
		webnotes.conn.sql("delete from `tabStock Ledger Entry`")
		webnotes.conn.sql("""delete from `tabBin`""")
		webnotes.conn.sql("""delete from `tabGL Entry`""")
		
		pro_bean = webnotes.bean(copy = test_records[0])
		pro_bean.insert()
		pro_bean.submit()
		
		from stock.doctype.stock_entry.test_stock_entry import test_records as se_test_records
		mr1 = webnotes.bean(copy = se_test_records[0])
		mr1.insert()
		mr1.submit()
		
		mr2 = webnotes.bean(copy = se_test_records[0])
		mr2.doclist[1].item_code = "_Test Item Home Desktop 100"
		mr2.insert()
		mr2.submit()
		
		stock_entry = make_stock_entry(pro_bean.doc.name, "Manufacture/Repack")
		stock_entry = webnotes.bean(stock_entry)
		
		stock_entry.doc.fg_completed_qty = 4
		stock_entry.run_method("get_items")
		stock_entry.submit()
		
		self.assertEqual(webnotes.conn.get_value("Production Order", pro_bean.doc.name, 
			"produced_qty"), 4)
		self.assertEqual(webnotes.conn.get_value("Bin", {"item_code": "_Test FG Item", 
			"warehouse": "_Test Warehouse 1 - _TC"}, "planned_qty"), 6)
			
		return pro_bean.doc.name
			
	def test_over_production(self):
		from stock.doctype.stock_entry.stock_entry import StockOverProductionError
		pro_order = self.test_planned_qty()
		
		stock_entry = make_stock_entry(pro_order, "Manufacture/Repack")
		stock_entry = webnotes.bean(stock_entry)
		
		stock_entry.doc.fg_completed_qty = 15
		stock_entry.run_method("get_items")
		stock_entry.insert()
		
		self.assertRaises(StockOverProductionError, stock_entry.submit)
			
		

test_records = [
	[
		{
			"bom_no": "BOM/_Test FG Item/001", 
			"company": "_Test Company", 
			"doctype": "Production Order", 
			"production_item": "_Test FG Item", 
			"qty": 10.0, 
			"fg_warehouse": "_Test Warehouse 1 - _TC",
			"wip_warehouse": "_Test Warehouse - _TC",
			"stock_uom": "Nos"
		}
	]
]