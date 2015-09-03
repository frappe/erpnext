# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from __future__ import unicode_literals
import unittest
import frappe
from frappe.utils import flt, time_diff_in_hours, now, add_days
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import set_perpetual_inventory
from erpnext.manufacturing.doctype.production_order.production_order \
	import make_stock_entry, ProductionNotApplicableError,ItemHasVariantError
from erpnext.stock.doctype.stock_entry import test_stock_entry
from erpnext.projects.doctype.time_log.time_log import OverProductionLoggedError

class TestProductionOrder(unittest.TestCase):
	def check_planned_qty(self):
		set_perpetual_inventory(0)

		planned0 = frappe.db.get_value("Bin", {"item_code": "_Test FG Item",
			"warehouse": "_Test Warehouse 1 - _TC"}, "planned_qty") or 0

		pro_order = make_prod_order_test_record()

		planned1 = frappe.db.get_value("Bin", {"item_code": "_Test FG Item",
			"warehouse": "_Test Warehouse 1 - _TC"}, "planned_qty")

		self.assertEqual(planned1, planned0 + 10)

		# add raw materials to stores
		test_stock_entry.make_stock_entry(item_code="_Test Item",
			target="Stores - _TC", qty=100, basic_rate=100)
		test_stock_entry.make_stock_entry(item_code="_Test Item Home Desktop 100",
			target="Stores - _TC", qty=100, basic_rate=100)

		# from stores to wip
		s = frappe.get_doc(make_stock_entry(pro_order.name, "Material Transfer for Manufacture", 4))
		for d in s.get("items"):
			d.s_warehouse = "Stores - _TC"
		s.insert()
		s.submit()

		# from wip to fg
		s = frappe.get_doc(make_stock_entry(pro_order.name, "Manufacture", 4))
		s.insert()
		s.submit()

		self.assertEqual(frappe.db.get_value("Production Order", pro_order.name, "produced_qty"), 4)

		planned2 = frappe.db.get_value("Bin", {"item_code": "_Test FG Item",
			"warehouse": "_Test Warehouse 1 - _TC"}, "planned_qty")

		self.assertEqual(planned2, planned0 + 6)

		return pro_order

	def test_over_production(self):
		from erpnext.manufacturing.doctype.production_order.production_order import StockOverProductionError
		pro_doc = self.check_planned_qty()

		test_stock_entry.make_stock_entry(item_code="_Test Item",
			target="_Test Warehouse - _TC", qty=100, basic_rate=100)
		test_stock_entry.make_stock_entry(item_code="_Test Item Home Desktop 100",
			target="_Test Warehouse - _TC", qty=100, basic_rate=100)

		s = frappe.get_doc(make_stock_entry(pro_doc.name, "Manufacture", 7))
		s.insert()

		self.assertRaises(StockOverProductionError, s.submit)

	def test_make_time_log(self):
		from erpnext.projects.doctype.time_log.test_time_log import make_time_log_test_record
		prod_order = make_prod_order_test_record(item="_Test FG Item 2",
			planned_start_date=now(), qty=1, do_not_save=True)

		prod_order.set_production_order_operations()
		prod_order.insert()
		prod_order.submit()

		d = prod_order.operations[0]

		d.completed_qty = flt(d.completed_qty)

		time_log = make_time_log_test_record(hours=1, production_order= prod_order.name, operation= d.operation,
			completed_qty= prod_order.qty - d.completed_qty, operation_id=d.name, for_manufacturing=1, simulate=True)

		self.assertEqual(prod_order.name, time_log.production_order)
		self.assertEqual((prod_order.qty - d.completed_qty), time_log.completed_qty)
		self.assertEqual(time_diff_in_hours(d.planned_end_time, d.planned_start_time),time_log.hours)
		
		manufacturing_settings = frappe.get_doc({
			"doctype": "Manufacturing Settings",
			"allow_production_on_holidays": 0
		})

		manufacturing_settings.save()

		prod_order.load_from_db()
		self.assertEqual(prod_order.operations[0].status, "Completed")
		self.assertEqual(prod_order.operations[0].completed_qty, prod_order.qty)

		self.assertEqual(prod_order.operations[0].actual_operation_time, 60)
		self.assertEqual(prod_order.operations[0].actual_operating_cost, 100)

		time_log.cancel()

		prod_order.load_from_db()
		self.assertEqual(prod_order.operations[0].status, "Pending")
		self.assertEqual(flt(prod_order.operations[0].completed_qty), 0)

		self.assertEqual(flt(prod_order.operations[0].actual_operation_time), 0)
		self.assertEqual(flt(prod_order.operations[0].actual_operating_cost), 0)

		time_log2 = make_time_log_test_record(from_time= add_days(time_log.to_time, 1) ,production_order= prod_order.name, operation= d.operation,
			completed_qty= 5, operation_id=d.name, for_manufacturing=1, do_not_save=True)

		self.assertRaises(OverProductionLoggedError, time_log2.save)

	def test_planned_operating_cost(self):
		prod_order = make_prod_order_test_record(item="_Test FG Item 2",
			planned_start_date=now(), qty=1, do_not_save=True)
		prod_order.set_production_order_operations()
		cost = prod_order.planned_operating_cost
		prod_order.qty = 2
		prod_order.set_production_order_operations()
		self.assertEqual(prod_order.planned_operating_cost, cost*2)

	def test_production_item(self):
		frappe.db.set_value("Item", "_Test FG Item", "is_pro_applicable", 0)

		prod_order = make_prod_order_test_record(item="_Test FG Item", qty=1, do_not_save=True)
		self.assertRaises(ProductionNotApplicableError, prod_order.save)

		frappe.db.set_value("Item", "_Test FG Item", "is_pro_applicable", 1)
		frappe.db.set_value("Item", "_Test FG Item", "end_of_life", "2000-1-1")

		self.assertRaises(frappe.ValidationError, prod_order.save)

		frappe.db.set_value("Item", "_Test FG Item", "end_of_life", None)

		prod_order = make_prod_order_test_record(item="_Test Variant Item", qty=1, do_not_save=True)
		self.assertRaises(ItemHasVariantError, prod_order.save)

def make_prod_order_test_record(**args):
	args = frappe._dict(args)

	pro_order = frappe.new_doc("Production Order")
	pro_order.production_item = args.production_item or args.item or args.item_code or "_Test FG Item"
	pro_order.bom_no = frappe.db.get_value("BOM", {"item": pro_order.production_item,
		"is_active": 1, "is_default": 1})
	pro_order.qty = args.qty or 10
	pro_order.wip_warehouse = args.wip_warehouse or "_Test Warehouse - _TC"
	pro_order.fg_warehouse = args.fg_warehouse or "_Test Warehouse 1 - _TC"
	pro_order.company = args.company or "_Test Company"
	pro_order.stock_uom = "_Test UOM"
	if args.planned_start_date:
		pro_order.planned_start_date = args.planned_start_date

	if not args.do_not_save:
		pro_order.insert()
		if not args.do_not_submit:
			pro_order.submit()
	return pro_order

test_records = frappe.get_test_records('Production Order')
