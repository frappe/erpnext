# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.manufacturing.doctype.work_order.mapper import make_stock_entry
from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
from erpnext.manufacturing.report.bom_variance_report.bom_variance_report import execute
from erpnext.stock.doctype.stock_entry import test_stock_entry
from erpnext.tests.utils import ERPNextTestSuite


class TestBOMVarianceReport(ERPNextTestSuite):
	def setUp(self):
		self.production_item = "_Test FG Item"
		self.warehouse = "_Test Warehouse - _TC"
		self.bom_no = frappe.db.get_value(
			"BOM", {"item": self.production_item, "is_active": 1, "is_default": 1}
		)
		self.raw_materials = self.get_bom_raw_materials()

		# allow over-production so a Work Order can produce more than planned; ERPNextTestSuite
		# rolls this back at tearDown, so no manual restore is needed
		frappe.db.set_single_value("Manufacturing Settings", "overproduction_percentage_for_work_order", 100)

	def get_bom_raw_materials(self):
		return {
			row.item_code: row.qty
			for row in frappe.get_all(
				"BOM Item", filters={"parent": self.bom_no}, fields=["item_code", "qty"]
			)
		}

	def create_over_produced_work_order(self, ordered_qty=2, produced_qty=3):
		work_order = make_wo_order_test_record(
			item=self.production_item,
			qty=ordered_qty,
			source_warehouse=self.warehouse,
			skip_transfer=1,
		)

		for item_code in self.raw_materials:
			test_stock_entry.make_stock_entry(
				item_code=item_code, target=self.warehouse, qty=100, basic_rate=100
			)

		stock_entry = frappe.get_doc(make_stock_entry(work_order.name, "Manufacture", produced_qty))
		stock_entry.submit()

		work_order.reload()
		self.assertEqual(work_order.produced_qty, produced_qty)
		return work_order

	def run_report(self, **extra):
		filters = frappe._dict({"bom_no": self.bom_no, **extra})
		return execute(filters)[1]

	def test_over_produced_work_order_appears_with_planned_and_actual(self):
		work_order = self.create_over_produced_work_order(ordered_qty=2, produced_qty=3)

		data = self.run_report(work_order=work_order.name)

		summary_rows = [row for row in data if row.get("work_order") == work_order.name]
		self.assertEqual(len(summary_rows), 1)

		summary = summary_rows[0]
		self.assertEqual(summary.get("production_item"), self.production_item)
		self.assertEqual(summary.get("bom_no"), self.bom_no)
		self.assertEqual(summary.get("qty"), 2)
		self.assertEqual(summary.get("produced_qty"), 3)

		raw_material_rows = {
			row.get("raw_material_code"): row for row in data if row.get("raw_material_code")
		}
		for item_code, per_unit_qty in self.raw_materials.items():
			self.assertIn(item_code, raw_material_rows)
			# planned/required qty scales with the ordered qty on the work order
			self.assertEqual(raw_material_rows[item_code].get("required_qty"), per_unit_qty * 2)

	def test_bom_no_filter_returns_over_produced_orders(self):
		work_order = self.create_over_produced_work_order(ordered_qty=2, produced_qty=3)

		data = self.run_report()

		matched = [row for row in data if row.get("work_order") == work_order.name]
		self.assertEqual(len(matched), 1)
		self.assertEqual(matched[0].get("bom_no"), self.bom_no)

	def test_unstarted_work_order_is_excluded(self):
		work_order = make_wo_order_test_record(
			item=self.production_item,
			qty=2,
			source_warehouse=self.warehouse,
			skip_transfer=1,
		)

		data = self.run_report(work_order=work_order.name)

		matched = [row for row in data if row.get("work_order") == work_order.name]
		self.assertEqual(matched, [])

	def test_work_order_produced_exactly_on_plan_is_excluded(self):
		# the canonical no-variance case: produced qty equals the planned qty, so the
		# report (which lists only over-produced orders) must not include it
		work_order = self.create_over_produced_work_order(ordered_qty=2, produced_qty=2)

		data = self.run_report(work_order=work_order.name)

		matched = [row for row in data if row.get("work_order") == work_order.name]
		self.assertEqual(matched, [])
