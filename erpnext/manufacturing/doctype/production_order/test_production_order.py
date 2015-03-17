# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from __future__ import unicode_literals
import unittest
import frappe
from frappe.utils import flt, get_datetime
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import set_perpetual_inventory
from erpnext.manufacturing.doctype.production_order.production_order import make_stock_entry
from erpnext.stock.doctype.stock_entry import test_stock_entry
from erpnext.projects.doctype.time_log.time_log import OverProductionLoggedError

class TestProductionOrder(unittest.TestCase):
	def check_planned_qty(self):
		set_perpetual_inventory(0)

		planned0 = frappe.db.get_value("Bin", {"item_code": "_Test FG Item", "warehouse": "_Test Warehouse 1 - _TC"}, "planned_qty") or 0

		pro_doc = frappe.copy_doc(test_records[0])
		pro_doc.insert()
		pro_doc.submit()

		# add raw materials to stores
		test_stock_entry.make_stock_entry(item_code="_Test Item",
			target="Stores - _TC", qty=100, incoming_rate=100)
		test_stock_entry.make_stock_entry(item_code="_Test Item Home Desktop 100",
			target="Stores - _TC", qty=100, incoming_rate=100)

		# from stores to wip
		s = frappe.get_doc(make_stock_entry(pro_doc.name, "Material Transfer for Manufacture", 4))
		for d in s.get("items"):
			d.s_warehouse = "Stores - _TC"
		s.fiscal_year = "_Test Fiscal Year 2013"
		s.posting_date = "2013-01-02"
		s.insert()
		s.submit()

		# from wip to fg
		s = frappe.get_doc(make_stock_entry(pro_doc.name, "Manufacture", 4))
		s.fiscal_year = "_Test Fiscal Year 2013"
		s.posting_date = "2013-01-03"
		s.insert()
		s.submit()

		self.assertEqual(frappe.db.get_value("Production Order", pro_doc.name,
			"produced_qty"), 4)
		planned1 = frappe.db.get_value("Bin", {"item_code": "_Test FG Item", "warehouse": "_Test Warehouse 1 - _TC"}, "planned_qty")

		self.assertEqual(planned1 - planned0, 6)

		return pro_doc

	def test_over_production(self):
		from erpnext.manufacturing.doctype.production_order.production_order import StockOverProductionError
		pro_doc = self.check_planned_qty()

		test_stock_entry.make_stock_entry(item_code="_Test Item",
			target="_Test Warehouse - _TC", qty=100, incoming_rate=100)
		test_stock_entry.make_stock_entry(item_code="_Test Item Home Desktop 100",
			target="_Test Warehouse - _TC", qty=100, incoming_rate=100)

		s = frappe.get_doc(make_stock_entry(pro_doc.name, "Manufacture", 7))
		s.fiscal_year = "_Test Fiscal Year 2013"
		s.posting_date = "2013-01-04"
		s.insert()

		self.assertRaises(StockOverProductionError, s.submit)

	def test_make_time_log(self):
		from erpnext.manufacturing.doctype.production_order.production_order import make_time_log
		from frappe.utils import cstr
		from frappe.utils import time_diff_in_hours

		prod_order = frappe.get_doc({
			"doctype": "Production Order",
			"production_item": "_Test FG Item 2",
			"bom_no": "BOM/_Test FG Item 2/001",
			"qty": 1,
			"wip_warehouse": "_Test Warehouse - _TC",
			"fg_warehouse": "_Test Warehouse 1 - _TC",
			"company": "_Test Company",
			"planned_start_date": "2014-11-25 00:00:00"
		})

		prod_order.set_production_order_operations()
		prod_order.insert()
		prod_order.submit()
		d = prod_order.operations[0]

		d.completed_qty = flt(d.completed_qty)

		time_log = make_time_log(prod_order.name, cstr(d.idx) + ". " + d.operation, \
			d.planned_start_time, d.planned_end_time, prod_order.qty - d.completed_qty,
			operation_id=d.name)

		self.assertEqual(prod_order.name, time_log.production_order)
		self.assertEqual((prod_order.qty - d.completed_qty), time_log.completed_qty)
		self.assertEqual(time_diff_in_hours(d.planned_end_time, d.planned_start_time),time_log.hours)

		time_log.save()
		time_log.submit()

		manufacturing_settings = frappe.get_doc({
			"doctype": "Manufacturing Settings",
			"allow_production_on_holidays": 0
		})

		manufacturing_settings.save()

		prod_order.load_from_db()
		self.assertEqual(prod_order.operations[0].status, "Completed")
		self.assertEqual(prod_order.operations[0].completed_qty, prod_order.qty)

		self.assertEqual(get_datetime(prod_order.operations[0].actual_start_time), get_datetime(time_log.from_time))
		self.assertEqual(get_datetime(prod_order.operations[0].actual_end_time), get_datetime(time_log.to_time))

		self.assertEqual(prod_order.operations[0].actual_operation_time, 60)
		self.assertEqual(prod_order.operations[0].actual_operating_cost, 100)

		time_log.cancel()

		prod_order.load_from_db()
		self.assertEqual(prod_order.operations[0].status, "Pending")
		self.assertEqual(flt(prod_order.operations[0].completed_qty), 0)

		self.assertEqual(flt(prod_order.operations[0].actual_operation_time), 0)
		self.assertEqual(flt(prod_order.operations[0].actual_operating_cost), 0)

		time_log2 = frappe.copy_doc(time_log)
		time_log2.update({
			"completed_qty": 10,
			"from_time": "2014-11-26 00:00:00",
			"to_time": "2014-11-26 00:00:00",
			"docstatus": 0
		})
		self.assertRaises(OverProductionLoggedError, time_log2.save)

test_records = frappe.get_test_records('Production Order')
