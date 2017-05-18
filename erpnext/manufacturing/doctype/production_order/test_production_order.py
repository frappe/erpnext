# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from __future__ import unicode_literals
import unittest
import frappe
from frappe.utils import flt, time_diff_in_hours, now, add_days, cint
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import set_perpetual_inventory
from erpnext.manufacturing.doctype.production_order.production_order \
	import make_stock_entry, ItemHasVariantError
from erpnext.stock.doctype.stock_entry import test_stock_entry
from erpnext.stock.doctype.item.test_item import get_total_projected_qty
from erpnext.stock.utils import get_bin
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

class TestProductionOrder(unittest.TestCase):
	def setUp(self):
		self.warehouse = '_Test Warehouse 2 - _TC'
		self.item = '_Test Item'

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

	def test_make_time_sheet(self):
		from erpnext.manufacturing.doctype.production_order.production_order import make_timesheet
		prod_order = make_prod_order_test_record(item="_Test FG Item 2",
			planned_start_date=now(), qty=1, do_not_save=True)

		prod_order.set_production_order_operations()
		prod_order.insert()
		prod_order.submit()
		
		d = prod_order.operations[0]
		d.completed_qty = flt(d.completed_qty)

		name = frappe.db.get_value('Timesheet', {'production_order': prod_order.name}, 'name')
		time_sheet_doc = frappe.get_doc('Timesheet', name)
		time_sheet_doc.submit()
		

		self.assertEqual(prod_order.name, time_sheet_doc.production_order)
		self.assertEqual((prod_order.qty - d.completed_qty), sum([d.completed_qty for d in time_sheet_doc.time_logs]))

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
		
		time_sheet_doc1 = make_timesheet(prod_order.name)
		self.assertEqual(len(time_sheet_doc1.get('time_logs')), 0)

		time_sheet_doc.cancel()

		prod_order.load_from_db()
		self.assertEqual(prod_order.operations[0].status, "Pending")
		self.assertEqual(flt(prod_order.operations[0].completed_qty), 0)

		self.assertEqual(flt(prod_order.operations[0].actual_operation_time), 0)
		self.assertEqual(flt(prod_order.operations[0].actual_operating_cost), 0)

	def test_planned_operating_cost(self):
		prod_order = make_prod_order_test_record(item="_Test FG Item 2",
			planned_start_date=now(), qty=1, do_not_save=True)
		prod_order.set_production_order_operations()
		cost = prod_order.planned_operating_cost
		prod_order.qty = 2
		prod_order.set_production_order_operations()
		self.assertEqual(prod_order.planned_operating_cost, cost*2)

	def test_production_item(self):
		prod_order = make_prod_order_test_record(item="_Test FG Item", qty=1, do_not_save=True)
		frappe.db.set_value("Item", "_Test FG Item", "end_of_life", "2000-1-1")

		self.assertRaises(frappe.ValidationError, prod_order.save)

		frappe.db.set_value("Item", "_Test FG Item", "end_of_life", None)
		frappe.db.set_value("Item", "_Test FG Item", "disabled", 1)

		self.assertRaises(frappe.ValidationError, prod_order.save)

		frappe.db.set_value("Item", "_Test FG Item", "disabled", 0)

		prod_order = make_prod_order_test_record(item="_Test Variant Item", qty=1, do_not_save=True)
		self.assertRaises(ItemHasVariantError, prod_order.save)

	def test_reserved_qty_for_production_submit(self):
		self.bin1_at_start = get_bin(self.item, self.warehouse)

		# reset to correct value
		self.bin1_at_start.update_reserved_qty_for_production()

		self.pro_order = make_prod_order_test_record(item="_Test FG Item", qty=2,
			source_warehouse=self.warehouse)

		self.bin1_on_submit = get_bin(self.item, self.warehouse)

		# reserved qty for production is updated
		self.assertEqual(cint(self.bin1_at_start.reserved_qty_for_production) + 2,
			cint(self.bin1_on_submit.reserved_qty_for_production))
		self.assertEqual(cint(self.bin1_at_start.projected_qty),
			cint(self.bin1_on_submit.projected_qty) + 2)

	def test_reserved_qty_for_production_cancel(self):
		self.test_reserved_qty_for_production_submit()

		self.pro_order.cancel()

		bin1_on_cancel = get_bin(self.item, self.warehouse)

		# reserved_qty_for_producion updated
		self.assertEqual(cint(self.bin1_at_start.reserved_qty_for_production),
			cint(bin1_on_cancel.reserved_qty_for_production))
		self.assertEqual(self.bin1_at_start.projected_qty,
			cint(bin1_on_cancel.projected_qty))

	def test_projected_qty_for_production_and_sales_order(self):
		before_production_order = get_bin(self.item, self.warehouse)
		before_production_order.update_reserved_qty_for_production()

		self.pro_order = make_prod_order_test_record(item="_Test FG Item", qty=2,
			source_warehouse=self.warehouse)

		after_production_order = get_bin(self.item, self.warehouse)

		sales_order = make_sales_order(item = self.item, qty = 2)
		after_sales_order = get_bin(self.item, self.warehouse)

		self.assertEqual(cint(before_production_order.reserved_qty_for_production) + 2,
			cint(after_sales_order.reserved_qty_for_production))
		self.assertEqual(cint(before_production_order.projected_qty),
			cint(after_sales_order.projected_qty) + 2)

		total_projected_qty = get_total_projected_qty(self.item)

		item_doc = frappe.get_doc('Item', self.item)
		self.assertEqual(total_projected_qty,  item_doc.total_projected_qty)

	def test_reserved_qty_for_production_on_stock_entry(self):
		test_stock_entry.make_stock_entry(item_code="_Test Item",
			target= self.warehouse, qty=100, basic_rate=100)
		test_stock_entry.make_stock_entry(item_code="_Test Item Home Desktop 100",
			target= self.warehouse, qty=100, basic_rate=100)

		self.test_reserved_qty_for_production_submit()

		s = frappe.get_doc(make_stock_entry(self.pro_order.name,
			"Material Transfer for Manufacture", 2))

		s.submit()

		bin1_on_start_production = get_bin(self.item, self.warehouse)

		# reserved_qty_for_producion updated
		self.assertEqual(cint(self.bin1_at_start.reserved_qty_for_production),
			cint(bin1_on_start_production.reserved_qty_for_production))

		# projected qty will now be 2 less (becuase of item movement)
		self.assertEqual(cint(self.bin1_at_start.projected_qty),
			cint(bin1_on_start_production.projected_qty) + 2)

		s = frappe.get_doc(make_stock_entry(self.pro_order.name, "Manufacture", 2))

		bin1_on_end_production = get_bin(self.item, self.warehouse)

		# no change in reserved / projected
		self.assertEqual(cint(bin1_on_end_production.reserved_qty_for_production),
			cint(bin1_on_start_production.reserved_qty_for_production))
		self.assertEqual(cint(bin1_on_end_production.projected_qty),
			cint(bin1_on_end_production.projected_qty))

		# required_items removed
		self.pro_order.reload()
		self.assertEqual(len(self.pro_order.required_items), 0)

	def test_scrap_material_qty(self):
		prod_order = make_prod_order_test_record(planned_start_date=now(), qty=2)

		# add raw materials to stores
		test_stock_entry.make_stock_entry(item_code="_Test Item",
			target="Stores - _TC", qty=10, basic_rate=5000.0)
		test_stock_entry.make_stock_entry(item_code="_Test Item Home Desktop 100",
			target="Stores - _TC", qty=10, basic_rate=1000.0)

		s = frappe.get_doc(make_stock_entry(prod_order.name, "Material Transfer for Manufacture", 2))
		for d in s.get("items"):
			d.s_warehouse = "Stores - _TC"
		s.insert()
		s.submit()

		s = frappe.get_doc(make_stock_entry(prod_order.name, "Manufacture", 2))
		s.insert()
		s.submit()

		prod_order_details = frappe.db.get_value("Production Order", prod_order.name,
			["scrap_warehouse", "qty", "produced_qty", "bom_no"], as_dict=1)

		scrap_item_details = get_scrap_item_details(prod_order_details.bom_no)

		self.assertEqual(prod_order_details.produced_qty, 2)

		for item in s.items:
			if item.bom_no and item.item_code in scrap_item_details:
				self.assertEqual(prod_order_details.scrap_warehouse, item.t_warehouse)
				self.assertEqual(flt(prod_order_details.qty)*flt(scrap_item_details[item.item_code]), item.qty)

def get_scrap_item_details(bom_no):
	scrap_items = {}
	for item in frappe.db.sql("""select item_code, qty from `tabBOM Scrap Item`
		where parent = %s""", bom_no, as_dict=1):
		scrap_items[item.item_code] = item.qty

	return scrap_items

def make_prod_order_test_record(**args):
	args = frappe._dict(args)

	pro_order = frappe.new_doc("Production Order")
	pro_order.production_item = args.production_item or args.item or args.item_code or "_Test FG Item"
	pro_order.bom_no = frappe.db.get_value("BOM", {"item": pro_order.production_item,
		"is_active": 1, "is_default": 1})
	pro_order.qty = args.qty or 10
	pro_order.wip_warehouse = args.wip_warehouse or "_Test Warehouse - _TC"
	pro_order.fg_warehouse = args.fg_warehouse or "_Test Warehouse 1 - _TC"
	pro_order.scrap_warehouse = args.fg_warehouse or "_Test Scrap Warehouse - _TC"
	pro_order.company = args.company or "_Test Company"
	pro_order.stock_uom = args.stock_uom or "_Test UOM"
	pro_order.use_multi_level_bom=0
	pro_order.set_production_order_operations()


	if args.source_warehouse:
		pro_order.source_warehouse = args.source_warehouse

	if args.planned_start_date:
		pro_order.planned_start_date = args.planned_start_date

	if not args.do_not_save:
		pro_order.insert()
		if not args.do_not_submit:
			pro_order.submit()
	return pro_order

test_records = frappe.get_test_records('Production Order')
