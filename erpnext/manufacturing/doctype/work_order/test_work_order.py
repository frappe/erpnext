# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from __future__ import unicode_literals
import unittest
import frappe
from frappe.utils import flt, time_diff_in_hours, now, add_days, cint
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import set_perpetual_inventory
from erpnext.manufacturing.doctype.work_order.work_order \
	import make_stock_entry, ItemHasVariantError, stop_unstop, StockOverProductionError, OverProductionError
from erpnext.stock.doctype.stock_entry import test_stock_entry
from erpnext.stock.utils import get_bin
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom

class TestWorkOrder(unittest.TestCase):
	def setUp(self):
		self.warehouse = '_Test Warehouse 2 - _TC'
		self.item = '_Test Item'

	def check_planned_qty(self):
		set_perpetual_inventory(0)

		planned0 = frappe.db.get_value("Bin", {"item_code": "_Test FG Item",
			"warehouse": "_Test Warehouse 1 - _TC"}, "planned_qty") or 0

		wo_order = make_wo_order_test_record()

		planned1 = frappe.db.get_value("Bin", {"item_code": "_Test FG Item",
			"warehouse": "_Test Warehouse 1 - _TC"}, "planned_qty")

		self.assertEqual(planned1, planned0 + 10)

		# add raw materials to stores
		test_stock_entry.make_stock_entry(item_code="_Test Item",
			target="Stores - _TC", qty=100, basic_rate=100)
		test_stock_entry.make_stock_entry(item_code="_Test Item Home Desktop 100",
			target="Stores - _TC", qty=100, basic_rate=100)

		# from stores to wip
		s = frappe.get_doc(make_stock_entry(wo_order.name, "Material Transfer for Manufacture", 4))
		for d in s.get("items"):
			d.s_warehouse = "Stores - _TC"
		s.insert()
		s.submit()

		# from wip to fg
		s = frappe.get_doc(make_stock_entry(wo_order.name, "Manufacture", 4))
		s.insert()
		s.submit()

		self.assertEqual(frappe.db.get_value("Work Order", wo_order.name, "produced_qty"), 4)

		planned2 = frappe.db.get_value("Bin", {"item_code": "_Test FG Item",
			"warehouse": "_Test Warehouse 1 - _TC"}, "planned_qty")

		self.assertEqual(planned2, planned0 + 6)

		return wo_order

	def test_over_production(self):
		wo_doc = self.check_planned_qty()

		test_stock_entry.make_stock_entry(item_code="_Test Item",
			target="_Test Warehouse - _TC", qty=100, basic_rate=100)
		test_stock_entry.make_stock_entry(item_code="_Test Item Home Desktop 100",
			target="_Test Warehouse - _TC", qty=100, basic_rate=100)

		s = frappe.get_doc(make_stock_entry(wo_doc.name, "Manufacture", 7))
		s.insert()

		self.assertRaises(StockOverProductionError, s.submit)

	def test_planned_operating_cost(self):
		wo_order = make_wo_order_test_record(item="_Test FG Item 2",
			planned_start_date=now(), qty=1, do_not_save=True)
		wo_order.set_work_order_operations()
		cost = wo_order.planned_operating_cost
		wo_order.qty = 2
		wo_order.set_work_order_operations()
		self.assertEqual(wo_order.planned_operating_cost, cost*2)

	def test_production_item(self):
		wo_order = make_wo_order_test_record(item="_Test FG Item", qty=1, do_not_save=True)
		frappe.db.set_value("Item", "_Test FG Item", "end_of_life", "2000-1-1")

		self.assertRaises(frappe.ValidationError, wo_order.save)

		frappe.db.set_value("Item", "_Test FG Item", "end_of_life", None)
		frappe.db.set_value("Item", "_Test FG Item", "disabled", 1)

		self.assertRaises(frappe.ValidationError, wo_order.save)

		frappe.db.set_value("Item", "_Test FG Item", "disabled", 0)

		wo_order = make_wo_order_test_record(item="_Test Variant Item", qty=1, do_not_save=True)
		self.assertRaises(ItemHasVariantError, wo_order.save)

	def test_reserved_qty_for_production_submit(self):
		self.bin1_at_start = get_bin(self.item, self.warehouse)

		# reset to correct value
		self.bin1_at_start.update_reserved_qty_for_production()

		self.wo_order = make_wo_order_test_record(item="_Test FG Item", qty=2,
			source_warehouse=self.warehouse)

		self.bin1_on_submit = get_bin(self.item, self.warehouse)

		# reserved qty for production is updated
		self.assertEqual(cint(self.bin1_at_start.reserved_qty_for_production) + 2,
			cint(self.bin1_on_submit.reserved_qty_for_production))
		self.assertEqual(cint(self.bin1_at_start.projected_qty),
			cint(self.bin1_on_submit.projected_qty) + 2)

	def test_reserved_qty_for_production_cancel(self):
		self.test_reserved_qty_for_production_submit()

		self.wo_order.cancel()

		bin1_on_cancel = get_bin(self.item, self.warehouse)

		# reserved_qty_for_producion updated
		self.assertEqual(cint(self.bin1_at_start.reserved_qty_for_production),
			cint(bin1_on_cancel.reserved_qty_for_production))
		self.assertEqual(self.bin1_at_start.projected_qty,
			cint(bin1_on_cancel.projected_qty))

	def test_reserved_qty_for_production_on_stock_entry(self):
		test_stock_entry.make_stock_entry(item_code="_Test Item",
			target= self.warehouse, qty=100, basic_rate=100)
		test_stock_entry.make_stock_entry(item_code="_Test Item Home Desktop 100",
			target= self.warehouse, qty=100, basic_rate=100)

		self.test_reserved_qty_for_production_submit()

		s = frappe.get_doc(make_stock_entry(self.wo_order.name,
			"Material Transfer for Manufacture", 2))

		s.submit()

		bin1_on_start_production = get_bin(self.item, self.warehouse)

		# reserved_qty_for_producion updated
		self.assertEqual(cint(self.bin1_at_start.reserved_qty_for_production),
			cint(bin1_on_start_production.reserved_qty_for_production))

		# projected qty will now be 2 less (becuase of item movement)
		self.assertEqual(cint(self.bin1_at_start.projected_qty),
			cint(bin1_on_start_production.projected_qty) + 2)

		s = frappe.get_doc(make_stock_entry(self.wo_order.name, "Manufacture", 2))

		bin1_on_end_production = get_bin(self.item, self.warehouse)

		# no change in reserved / projected
		self.assertEqual(cint(bin1_on_end_production.reserved_qty_for_production),
			cint(bin1_on_start_production.reserved_qty_for_production))
		self.assertEqual(cint(bin1_on_end_production.projected_qty),
			cint(bin1_on_end_production.projected_qty))

	def test_reserved_qty_for_stopped_production(self):
		test_stock_entry.make_stock_entry(item_code="_Test Item",
			target= self.warehouse, qty=100, basic_rate=100)
		test_stock_entry.make_stock_entry(item_code="_Test Item Home Desktop 100",
			target= self.warehouse, qty=100, basic_rate=100)

		# 	0 0 0

		self.test_reserved_qty_for_production_submit()

		#2 0 -2

		s = frappe.get_doc(make_stock_entry(self.wo_order.name,
			"Material Transfer for Manufacture", 1))

		s.submit()

		#1 -1 0

		bin1_on_start_production = get_bin(self.item, self.warehouse)

		# reserved_qty_for_producion updated
		self.assertEqual(cint(self.bin1_at_start.reserved_qty_for_production) + 1,
			cint(bin1_on_start_production.reserved_qty_for_production))

		# projected qty will now be 2 less (becuase of item movement)
		self.assertEqual(cint(self.bin1_at_start.projected_qty),
			cint(bin1_on_start_production.projected_qty) + 2)

		# STOP
		stop_unstop(self.wo_order.name, "Stopped")

		bin1_on_stop_production = get_bin(self.item, self.warehouse)

		# no change in reserved / projected
		self.assertEqual(cint(bin1_on_stop_production.reserved_qty_for_production),
			cint(self.bin1_at_start.reserved_qty_for_production))
		self.assertEqual(cint(bin1_on_stop_production.projected_qty) + 1,
			cint(self.bin1_at_start.projected_qty))

	def test_scrap_material_qty(self):
		wo_order = make_wo_order_test_record(planned_start_date=now(), qty=2)

		# add raw materials to stores
		test_stock_entry.make_stock_entry(item_code="_Test Item",
			target="Stores - _TC", qty=10, basic_rate=5000.0)
		test_stock_entry.make_stock_entry(item_code="_Test Item Home Desktop 100",
			target="Stores - _TC", qty=10, basic_rate=1000.0)

		s = frappe.get_doc(make_stock_entry(wo_order.name, "Material Transfer for Manufacture", 2))
		for d in s.get("items"):
			d.s_warehouse = "Stores - _TC"
		s.insert()
		s.submit()

		s = frappe.get_doc(make_stock_entry(wo_order.name, "Manufacture", 2))
		s.insert()
		s.submit()

		wo_order_details = frappe.db.get_value("Work Order", wo_order.name,
			["scrap_warehouse", "qty", "produced_qty", "bom_no"], as_dict=1)

		scrap_item_details = get_scrap_item_details(wo_order_details.bom_no)

		self.assertEqual(wo_order_details.produced_qty, 2)

		for item in s.items:
			if item.bom_no and item.item_code in scrap_item_details:
				self.assertEqual(wo_order_details.scrap_warehouse, item.t_warehouse)
				self.assertEqual(flt(wo_order_details.qty)*flt(scrap_item_details[item.item_code]), item.qty)

	def test_allow_overproduction(self):
		allow_overproduction("overproduction_percentage_for_work_order", 0)
		wo_order = make_wo_order_test_record(planned_start_date=now(), qty=2)
		test_stock_entry.make_stock_entry(item_code="_Test Item",
			target="_Test Warehouse - _TC", qty=10, basic_rate=5000.0)
		test_stock_entry.make_stock_entry(item_code="_Test Item Home Desktop 100",
			target="_Test Warehouse - _TC", qty=10, basic_rate=1000.0)

		s = frappe.get_doc(make_stock_entry(wo_order.name, "Material Transfer for Manufacture", 3))
		s.insert()
		self.assertRaises(StockOverProductionError, s.submit)

		allow_overproduction("overproduction_percentage_for_work_order", 50)
		s.load_from_db()
		s.submit()
		self.assertEqual(s.docstatus, 1)

		allow_overproduction("overproduction_percentage_for_work_order", 0)

	def test_over_production_for_sales_order(self):
		so = make_sales_order(item_code="_Test FG Item", qty=2)

		allow_overproduction("overproduction_percentage_for_sales_order", 0)
		wo_order = make_wo_order_test_record(planned_start_date=now(),
			sales_order=so.name, qty=3, do_not_save=True)

		self.assertRaises(OverProductionError, wo_order.save)

		allow_overproduction("overproduction_percentage_for_sales_order", 50)
		wo_order = make_wo_order_test_record(planned_start_date=now(),
			sales_order=so.name, qty=3)

		wo_order.submit()
		self.assertEqual(wo_order.docstatus, 1)

		allow_overproduction("overproduction_percentage_for_sales_order", 0)

	def test_work_order_with_non_stock_item(self):
		items = {'Finished Good Test Item For non stock': 1, '_Test FG Item': 1, '_Test FG Non Stock Item': 0}
		for item, is_stock_item in items.items():
			make_item(item, {
				'is_stock_item': is_stock_item
			})

		if not frappe.db.get_value('Item Price', {'item_code': '_Test FG Non Stock Item'}):
			frappe.get_doc({
				'doctype': 'Item Price',
				'item_code': '_Test FG Non Stock Item',
				'price_list_rate': 1000,
				'price_list': 'Standard Buying'
			}).insert(ignore_permissions=True)

		fg_item = 'Finished Good Test Item For non stock'
		test_stock_entry.make_stock_entry(item_code="_Test FG Item",
			target="_Test Warehouse - _TC", qty=1, basic_rate=100)

		if not frappe.db.get_value('BOM', {'item': fg_item}):
			make_bom(item=fg_item, rate=1000, raw_materials = ['_Test FG Item', '_Test FG Non Stock Item'])

		wo = make_wo_order_test_record(production_item = fg_item)

		se = frappe.get_doc(make_stock_entry(wo.name, "Material Transfer for Manufacture", 1))
		se.insert()
		se.submit()

		ste = frappe.get_doc(make_stock_entry(wo.name, "Manufacture", 1))
		ste.insert()
		self.assertEqual(len(ste.additional_costs), 1)
		self.assertEqual(ste.total_additional_costs, 1000)

	def test_work_order_with_non_transfer_item(self):
		items = {'Finished Good Transfer Item': 1, '_Test FG Item': 1, '_Test FG Item 1': 0}
		for item, allow_transfer in items.items():
			make_item(item, {
				'include_item_in_manufacturing': allow_transfer
			})

		fg_item = 'Finished Good Transfer Item'
		test_stock_entry.make_stock_entry(item_code="_Test FG Item",
			target="_Test Warehouse - _TC", qty=1, basic_rate=100)
		test_stock_entry.make_stock_entry(item_code="_Test FG Item 1",
			target="_Test Warehouse - _TC", qty=1, basic_rate=100)

		if not frappe.db.get_value('BOM', {'item': fg_item}):
			make_bom(item=fg_item, raw_materials = ['_Test FG Item', '_Test FG Item 1'])

		wo = make_wo_order_test_record(production_item = fg_item)
		ste = frappe.get_doc(make_stock_entry(wo.name, "Material Transfer for Manufacture", 1))
		ste.insert()
		ste.submit()
		self.assertEqual(len(ste.items), 1)
		ste1 = frappe.get_doc(make_stock_entry(wo.name, "Manufacture", 1))
		self.assertEqual(len(ste1.items), 3)

def get_scrap_item_details(bom_no):
	scrap_items = {}
	for item in frappe.db.sql("""select item_code, stock_qty from `tabBOM Scrap Item`
		where parent = %s""", bom_no, as_dict=1):
		scrap_items[item.item_code] = item.stock_qty

	return scrap_items

def allow_overproduction(fieldname, percentage):
	doc = frappe.get_doc("Manufacturing Settings")
	doc.update({
		fieldname: percentage
	})
	doc.save()

def make_wo_order_test_record(**args):
	args = frappe._dict(args)

	wo_order = frappe.new_doc("Work Order")
	wo_order.production_item = args.production_item or args.item or args.item_code or "_Test FG Item"
	wo_order.bom_no = frappe.db.get_value("BOM", {"item": wo_order.production_item,
		"is_active": 1, "is_default": 1})
	wo_order.qty = args.qty or 10
	wo_order.wip_warehouse = args.wip_warehouse or "_Test Warehouse - _TC"
	wo_order.fg_warehouse = args.fg_warehouse or "_Test Warehouse 1 - _TC"
	wo_order.scrap_warehouse = args.fg_warehouse or "_Test Scrap Warehouse - _TC"
	wo_order.company = args.company or "_Test Company"
	wo_order.stock_uom = args.stock_uom or "_Test UOM"
	wo_order.use_multi_level_bom=0
	wo_order.skip_transfer=1
	wo_order.get_items_and_operations_from_bom()
	wo_order.sales_order = args.sales_order or None

	if args.source_warehouse:
		for item in wo_order.get("required_items"):
			item.source_warehouse = args.source_warehouse

	if args.planned_start_date:
		wo_order.planned_start_date = args.planned_start_date

	if not args.do_not_save:
		wo_order.insert()

		if not args.do_not_submit:
			wo_order.submit()
	return wo_order

test_records = frappe.get_test_records('Work Order')
