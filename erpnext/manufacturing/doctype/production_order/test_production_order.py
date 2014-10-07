# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from __future__ import unicode_literals
import unittest
import frappe
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import set_perpetual_inventory
from erpnext.manufacturing.doctype.production_order.production_order import make_stock_entry
from erpnext.stock.doctype.stock_entry import test_stock_entry

class TestProductionOrder(unittest.TestCase):
	def test_planned_qty(self):
		set_perpetual_inventory(0)

		planned0 = frappe.db.get_value("Bin", {"item_code": "_Test FG Item", "warehouse": "_Test Warehouse 1 - _TC"}, "planned_qty") or 0

		pro_doc = frappe.copy_doc(test_records[0])
		pro_doc.insert()
		pro_doc.submit()

		# add raw materials to stores
		test_stock_entry.make_stock_entry("_Test Item", None, "Stores - _TC", 100, 100)
		test_stock_entry.make_stock_entry("_Test Item Home Desktop 100", None, "Stores - _TC", 100, 100)

		# from stores to wip
		s = frappe.get_doc(make_stock_entry(pro_doc.name, "Material Transfer", 4))
		for d in s.get("mtn_details"):
			d.s_warehouse = "Stores - _TC"
		s.insert()
		s.submit()

		# from wip to fg
		s = frappe.get_doc(make_stock_entry(pro_doc.name, "Manufacture", 4))
		s.insert()
		s.submit()

		self.assertEqual(frappe.db.get_value("Production Order", pro_doc.name,
			"produced_qty"), 4)
		planned1 = frappe.db.get_value("Bin", {"item_code": "_Test FG Item", "warehouse": "_Test Warehouse 1 - _TC"}, "planned_qty")
		self.assertEqual(planned1 - planned0, 6)

		return pro_doc

	def test_over_production(self):
		from erpnext.manufacturing.doctype.production_order.production_order import StockOverProductionError
		pro_doc = self.test_planned_qty()

		test_stock_entry.make_stock_entry("_Test Item", None, "_Test Warehouse - _TC", 100, 100)
		test_stock_entry.make_stock_entry("_Test Item Home Desktop 100", None, "_Test Warehouse - _TC", 100, 100)

		s = frappe.get_doc(make_stock_entry(pro_doc.name, "Manufacture", 7))
		s.insert()

		self.assertRaises(StockOverProductionError, s.submit)

test_records = frappe.get_test_records('Production Order')