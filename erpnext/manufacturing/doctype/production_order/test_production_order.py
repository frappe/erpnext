# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from __future__ import unicode_literals
import unittest
import frappe
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import set_perpetual_inventory
from erpnext.manufacturing.doctype.production_order.production_order import make_stock_entry


class TestProductionOrder(unittest.TestCase):
	def test_planned_qty(self):
		set_perpetual_inventory(0)
		pro_doc = frappe.copy_doc(test_records[0])
		pro_doc.insert()
		pro_doc.submit()

		# add raw materials to stores
		s = frappe.new_doc("Stock Entry")
		s.purpose = "Material Receipt"
		s.company = "_Test Company"
		s.append("mtn_details", {
			"item_code": "_Test Item",
			"t_warehouse": "Stores - _TC",
			"qty": 100,
			"incoming_rate": 5000
		})
		s.insert()
		s.submit()

		# add raw materials to stores
		s = frappe.new_doc("Stock Entry")
		s.purpose = "Material Receipt"
		s.company = "_Test Company"
		s.append("mtn_details", {
			"item_code": "_Test Item Home Desktop 100",
			"t_warehouse": "Stores - _TC",
			"qty": 100,
			"incoming_rate": 1000
		})
		s.insert()
		s.submit()

		# from stores to wip
		s = frappe.get_doc(make_stock_entry(pro_doc.name, "Material Transfer", 4))
		for d in s.get("mtn_details"):
			d.s_warehouse = "Stores - _TC"
		s.insert()
		s.submit()

		# from wip to fg
		s = frappe.get_doc(make_stock_entry(pro_doc.name, "Manufacture/Repack", 4))
		s.insert()
		s.submit()

		self.assertEqual(frappe.db.get_value("Production Order", pro_doc.name,
			"produced_qty"), 4)
		self.assertEqual(frappe.db.get_value("Bin", {"item_code": "_Test FG Item",
			"warehouse": "_Test Warehouse 1 - _TC"}, "planned_qty"), 6)

		return pro_doc

	def test_over_production(self):
		from erpnext.manufacturing.doctype.production_order.production_order import StockOverProductionError
		pro_doc = self.test_planned_qty()

		s = frappe.get_doc(make_stock_entry(pro_doc.name, "Material Transfer", 7))
		for d in s.get("mtn_details"):
			d.s_warehouse = "Stores - _TC"
		s.insert()
		s.submit()

		s = frappe.get_doc(make_stock_entry(pro_doc.name, "Manufacture/Repack", 7))
		s.insert()

		self.assertRaises(StockOverProductionError, s.submit)


test_records = frappe.get_test_records('Production Order')
