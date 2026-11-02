# Copyright (c) 2017, Velometro Mobility Inc and contributors
# For license information, please see license.txt

import frappe

from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
from erpnext.manufacturing.doctype.work_order.mapper import make_stock_entry
from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
from erpnext.manufacturing.doctype.work_order.work_order import close_work_order, stop_unstop
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

	def test_transferred_stock_is_not_counted_again_for_another_order(self):
		wip = "_Test Warehouse 2 - _TC"
		first, material = self.make_stocked_work_order(wip_warehouse=wip)
		frappe.get_doc(make_stock_entry(first.name, "Material Transfer for Manufacture", 10)).submit()
		second = make_wo_order_test_record(
			item=first.production_item, bom_no=first.bom_no, qty=10, source_warehouse=wip
		)

		self.assertEqual(self.get_rows(first.name)[material].ready_to_build, "Y")
		self.assertEqual(self.get_rows(second.name)[material].ready_to_build, "N")

	def test_substitute_transfer_does_not_hide_the_original_item_in_wip(self):
		wip = "_Test Warehouse 2 - _TC"
		material = make_item(
			properties={"is_stock_item": 1, "valuation_rate": 10, "allow_alternative_item": 1}
		).name
		substitute = make_item(properties={"is_stock_item": 1, "valuation_rate": 10}).name
		frappe.get_doc(
			{"doctype": "Item Alternative", "item_code": material, "alternative_item_code": substitute}
		).insert()
		fg_item = make_item(properties={"is_stock_item": 1}).name
		bom = make_bom(item=fg_item, raw_materials=[material])
		test_stock_entry.make_stock_entry(item_code=substitute, target=STORES, qty=10, basic_rate=10)
		test_stock_entry.make_stock_entry(item_code=material, target=wip, qty=10, basic_rate=10)
		first = make_wo_order_test_record(
			item=fg_item,
			bom_no=bom.name,
			qty=10,
			source_warehouse=STORES,
			wip_warehouse=wip,
			do_not_submit=True,
		)
		first.allow_alternative_item = 1
		for row in first.required_items:
			row.allow_alternative_item = 1
		first.submit()
		transfer = frappe.get_doc(make_stock_entry(first.name, "Material Transfer for Manufacture", 10))
		transfer.items[0].update({"item_code": substitute, "original_item": material})
		transfer.submit()
		second = make_wo_order_test_record(item=fg_item, bom_no=bom.name, qty=10, source_warehouse=wip)

		self.assertEqual(self.get_rows(second.name)[material].ready_to_build, "Y")

	def held_in_wip(self, work_order):
		from erpnext.manufacturing.report.work_order_stock_report.work_order_stock_report import (
			get_stock_held_in_wip,
		)

		return get_stock_held_in_wip([frappe._dict(name=work_order.name)])

	@ERPNextTestSuite.change_settings("Manufacturing Settings", {"material_consumption": 1})
	def test_separately_consumed_stock_is_no_longer_held(self):
		wip = "_Test Warehouse 2 - _TC"
		wo, material = self.make_stocked_work_order(wip_warehouse=wip)
		frappe.get_doc(make_stock_entry(wo.name, "Material Transfer for Manufacture", 10)).submit()
		frappe.get_doc(make_stock_entry(wo.name, "Material Consumption for Manufacture", 6)).submit()

		self.assertEqual(self.held_in_wip(wo), {(material, wip): 4})

	def test_returned_stock_is_no_longer_held(self):
		from unittest.mock import patch

		from erpnext.manufacturing.report.work_order_stock_report.work_order_stock_report import (
			get_stock_held_in_wip,
		)

		def moves(wo_list, purpose, is_return, field):
			if purpose != "Material Transfer for Manufacture":
				return []
			qty, warehouse = (4, "WIP") if is_return else (10, "WIP")
			return [frappe._dict(work_order="A", item_code="RM", warehouse=warehouse, qty=qty)]

		with patch(
			"erpnext.manufacturing.report.work_order_stock_report.work_order_stock_report.get_work_order_stock_moves",
			side_effect=moves,
		):
			held = get_stock_held_in_wip([frappe._dict(name="A")])

		self.assertEqual(held, {("RM", "WIP"): 6})

	def test_one_order_consumption_does_not_release_another_order_stock(self):
		from unittest.mock import patch

		from erpnext.manufacturing.report.work_order_stock_report.work_order_stock_report import (
			get_stock_held_in_wip,
		)

		moves = {
			"Material Transfer for Manufacture": [
				frappe._dict(work_order="A", item_code="RM", warehouse="WIP", qty=10)
			],
			"Manufacture": [frappe._dict(work_order="B", item_code="RM", warehouse="WIP", qty=10)],
		}
		with patch(
			"erpnext.manufacturing.report.work_order_stock_report.work_order_stock_report.get_work_order_stock_moves",
			side_effect=lambda wo_list, purpose, is_return, field: moves.get(purpose, [])
			if not is_return
			else [],
		):
			held = get_stock_held_in_wip([frappe._dict(name="A"), frappe._dict(name="B")])

		self.assertEqual(held, {("RM", "WIP"): 10})

	def test_rows_are_listed_by_work_order_name(self):
		from frappe.utils import add_days, now_datetime

		later, material = self.make_stocked_work_order()
		earlier = make_wo_order_test_record(
			item=later.production_item,
			bom_no=later.bom_no,
			qty=10,
			source_warehouse=STORES,
			planned_start_date=add_days(now_datetime(), -5),
		)

		names = [
			row.work_order
			for row in execute(frappe._dict())[1]
			if row.work_order in (later.name, earlier.name)
		]

		self.assertEqual(names, sorted(names))
		self.assertEqual(self.get_rows(earlier.name)[material].ready_to_build, "Y")

	def test_closed_and_stopped_work_orders_are_left_out(self):
		closed, _material = self.make_stocked_work_order(wip_warehouse="_Test Warehouse 2 - _TC")
		frappe.get_doc(make_stock_entry(closed.name, "Material Transfer for Manufacture", 10)).submit()
		close_work_order(closed.name, "Closed")
		stopped, _material = self.make_stocked_work_order(wip_warehouse="_Test Warehouse 2 - _TC")
		frappe.get_doc(make_stock_entry(stopped.name, "Material Transfer for Manufacture", 10)).submit()
		stop_unstop(stopped.name, "Stopped")

		self.assertEqual(self.get_rows(closed.name, warehouse=STORES), {})
		self.assertEqual(self.get_rows(stopped.name, warehouse=STORES), {})

	def test_warehouse_filter_limits_the_rows(self):
		wo, material = self.make_stocked_work_order()

		self.assertIn(material, self.get_rows(wo.name, warehouse=STORES))
		self.assertEqual(self.get_rows(wo.name, warehouse="_Test Warehouse 1 - _TC"), {})

	def test_stock_is_shared_out_between_work_orders(self):
		first, material = self.make_stocked_work_order()
		second = make_wo_order_test_record(
			item=first.production_item, bom_no=first.bom_no, qty=10, source_warehouse=STORES
		)

		self.assertEqual(self.get_rows(first.name, warehouse=STORES)[material].ready_to_build, "Y")
		self.assertEqual(self.get_rows(second.name, warehouse=STORES)[material].ready_to_build, "N")
