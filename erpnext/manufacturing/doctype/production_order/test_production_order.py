# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from __future__ import unicode_literals
import unittest
import frappe
from frappe.utils import cstr, getdate
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import set_perpetual_inventory
from erpnext.manufacturing.doctype.production_order.production_order import make_stock_entry


class TestProductionOrder(unittest.TestCase):
	def test_planned_qty(self):
		set_perpetual_inventory(0)
		frappe.db.sql("delete from `tabStock Ledger Entry`")
		frappe.db.sql("""delete from `tabBin`""")
		frappe.db.sql("""delete from `tabGL Entry`""")
		
		pro_doc = frappe.copy_doc(test_records[0])
		pro_doc.insert()
		pro_doc.submit()
		
		from erpnext.stock.doctype.stock_entry.test_stock_entry import test_records as se_test_records
		mr1 = frappe.copy_doc(se_test_records[0])
		mr1.insert()
		mr1.submit()
		
		mr2 = frappe.copy_doc(se_test_records[0])
		mr2["mtn_details"][0].item_code = "_Test Item Home Desktop 100"
		mr2.insert()
		mr2.submit()
		
		stock_entry = make_stock_entry(pro_doc.name, "Manufacture/Repack")
		stock_entry = frappe.get_doc(stock_entry)
		stock_entry.fiscal_year = "_Test Fiscal Year 2013"
		stock_entry.fg_completed_qty = 4
		stock_entry.posting_date = "2013-05-12"
		stock_entry.fiscal_year = "_Test Fiscal Year 2013"
		stock_entry.run_method("get_items")
		stock_entry.submit()
		
		self.assertEqual(frappe.db.get_value("Production Order", pro_doc.name, 
			"produced_qty"), 4)
		self.assertEqual(frappe.db.get_value("Bin", {"item_code": "_Test FG Item", 
			"warehouse": "_Test Warehouse 1 - _TC"}, "planned_qty"), 6)
			
		return pro_doc.name
			
	def test_over_production(self):
		from erpnext.stock.doctype.stock_entry.stock_entry import StockOverProductionError
		pro_order = self.test_planned_qty()
		
		stock_entry = make_stock_entry(pro_order, "Manufacture/Repack")
		stock_entry = frappe.get_doc(stock_entry)
		stock_entry.posting_date = "2013-05-12"
		stock_entry.fiscal_year = "_Test Fiscal Year 2013"
		stock_entry.fg_completed_qty = 15
		stock_entry.run_method("get_items")
		stock_entry.insert()
		
		self.assertRaises(StockOverProductionError, stock_entry.submit)
			
		

test_records = frappe.get_test_records('Production Order')