# Copyright (c) 2017, Velometro Mobility Inc and contributors
# For license information, please see license.txt

import frappe

from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
from erpnext.manufacturing.doctype.work_order.mapper import make_stock_entry
from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
from erpnext.manufacturing.report.work_order_stock_report.work_order_stock_report import execute
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry import test_stock_entry
from erpnext.tests.utils import ERPNextTestSuite

STORES = "_Test Warehouse - _TC"


class TestWorkOrderStockReport(ERPNextTestSuite):
	def test_report_executes_and_lists_work_order(self):
		# get_item_list aggregates build_qty with Max() and groups by item_code, so it returns one
		# row per item_code and runs on Postgres (which rejects non-grouped selected columns).
		# This exercises that query on both engines.
		from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
		from erpnext.manufacturing.report.work_order_stock_report.work_order_stock_report import execute

		wo = make_wo_order_test_record(
			production_item="_Test FG Item", qty=1, source_warehouse="_Test Warehouse - _TC"
		)

		columns, data = execute(frappe._dict(warehouse="_Test Warehouse - _TC"))

		self.assertTrue(columns)
		self.assertIn(wo.name, {row["work_order"] for row in data})

	def test_item_listed_twice_in_bom_is_counted_once(self):
		# A BOM may list the same raw item on multiple lines at different qty (validate_materials does
		# not dedupe). get_item_list aggregates the qty columns and groups by item_code only, so the
		# report stays one row per item — matching the original MariaDB output. The pre-fix multi-column
		# GROUP BY split such an item into one row per distinct stock_qty, inflating "# Req'd Items".
		from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
		from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
		from erpnext.manufacturing.report.work_order_stock_report.work_order_stock_report import execute
		from erpnext.stock.doctype.item.test_item import make_item

		fg_item = make_item("_Test WO Stock Dup FG", {"is_stock_item": 1}).name
		rm_item = "_Test Item"

		bom = make_bom(item=fg_item, raw_materials=[rm_item], rm_qty=1, currency="INR", do_not_save=True)
		# a second line for the same raw item at a different qty -> a different stock_qty
		first = bom.items[0]
		bom.append(
			"items",
			{
				"item_code": rm_item,
				"qty": 2,
				"uom": first.uom,
				"stock_uom": first.stock_uom,
				"rate": first.rate,
			},
		)
		bom.insert(ignore_permissions=True)
		bom.submit()

		wo = make_wo_order_test_record(
			production_item=fg_item,
			bom_no=bom.name,
			qty=1,
			source_warehouse="_Test Warehouse - _TC",
			skip_transfer=1,
		)

		columns, data = execute(frappe._dict(warehouse="_Test Warehouse - _TC"))

		wo_rows = [row for row in data if row["work_order"] == wo.name]
		self.assertTrue(wo_rows)
		# the duplicated raw item must be counted once per work order item, not once per BOM line
		for row in wo_rows:
			self.assertEqual(row["req_items"], 1)

	def get_rows(self, work_order, **filters):
		data = execute(frappe._dict(filters))[1]
		return {row.item_code: row for row in data if row.work_order == work_order}

	def make_stocked_work_order(self, qty=10, stock_qty=10, **kwargs):
		material = make_item(properties={"is_stock_item": 1, "valuation_rate": 10}).name
		fg_item = make_item(properties={"is_stock_item": 1}).name
		bom = make_bom(item=fg_item, raw_materials=[material])
		if stock_qty:
			test_stock_entry.make_stock_entry(item_code=material, target=STORES, qty=stock_qty, basic_rate=10)
		wo = make_wo_order_test_record(
			item=fg_item, bom_no=bom.name, qty=qty, source_warehouse=STORES, **kwargs
		)
		return wo, material

	def test_multi_level_materials_are_checked_against_stock(self):
		sub_material = make_item(properties={"is_stock_item": 1, "valuation_rate": 10}).name
		sub_assembly = make_item(properties={"is_stock_item": 1}).name
		make_bom(item=sub_assembly, raw_materials=[sub_material], rm_qty=2)
		fg_item = make_item(properties={"is_stock_item": 1}).name
		bom = make_bom(item=fg_item, raw_materials=[sub_assembly])
		wo = make_wo_order_test_record(
			item=fg_item, bom_no=bom.name, qty=10, source_warehouse=STORES, use_multi_level_bom=1
		)

		row = self.get_rows(wo.name, warehouse=STORES)[sub_material]

		self.assertEqual((row.instock, row.buildable_qty, row.ready_to_build), (0, 0, "N"))

	def test_material_in_wip_counts_as_available(self):
		wo, material = self.make_stocked_work_order(wip_warehouse="_Test Warehouse 2 - _TC")
		frappe.get_doc(make_stock_entry(wo.name, "Material Transfer for Manufacture", 10)).submit()

		row = self.get_rows(wo.name, warehouse=STORES)[material]

		self.assertEqual((row.instock, row.buildable_qty, row.ready_to_build), (1, 10, "Y"))
