# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.manufacturing.doctype.production_plan.test_production_plan import create_production_plan
from erpnext.manufacturing.doctype.work_order.mapper import make_stock_entry as make_se_from_wo
from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
from erpnext.manufacturing.report.production_plan_summary.production_plan_summary import execute
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.tests.utils import ERPNextTestSuite


class TestProductionPlanSummary(ERPNextTestSuite):
	def run_report(self, production_plan):
		filters = frappe._dict({"production_plan": production_plan})
		return execute(filters)[1]

	def make_plan(self, planned_qty=2):
		return create_production_plan(
			item_code="_Test FG Item",
			planned_qty=planned_qty,
			skip_getting_mr_items=1,
		)

	def make_submitted_work_order(self, plan, qty):
		wo = make_wo_order_test_record(
			item_code="_Test FG Item",
			qty=qty,
			company=plan.company,
			wip_warehouse="Work In Progress - _TC",
			fg_warehouse="Finished Goods - _TC",
			skip_transfer=1,
			use_multi_level_bom=1,
			do_not_submit=True,
		)
		wo.production_plan = plan.name
		wo.production_plan_item = plan.po_items[0].name
		wo.submit()
		return wo

	def stock_required_materials(self, wo):
		# make sure every raw material is available in its source warehouse before manufacturing,
		# otherwise a clean database raises NegativeStockError
		for item in wo.required_items:
			make_stock_entry(
				item_code=item.item_code,
				to_warehouse=item.source_warehouse or "_Test Warehouse - _TC",
				qty=item.required_qty + 10,
				rate=100,
			)

	def get_work_order_row(self, data, item_code):
		for row in data:
			if row.get("item_code") == item_code and row.get("document_type") == "Work Order":
				return row
		return None

	def get_summary_row(self, data, item_code):
		for row in data:
			if row.get("item_code") == item_code and not row.get("document_type"):
				return row
		return None

	def test_summary_without_work_order(self):
		"""A submitted plan with no work order still yields a summary row for the planned item."""
		plan = self.make_plan(planned_qty=2)

		data = self.run_report(plan.name)
		summary = self.get_summary_row(data, "_Test FG Item")

		self.assertIsNotNone(summary)
		self.assertEqual(summary.get("qty"), 2)
		self.assertEqual(summary.get("produced_qty"), 0)
		# nothing produced yet, so the whole planned qty is pending
		self.assertEqual(summary.get("pending_qty"), 2)
		self.assertIsNone(self.get_work_order_row(data, "_Test FG Item"))

	def test_summary_with_pending_work_order(self):
		"""An unproduced work order shows full planned qty as pending."""
		plan = self.make_plan(planned_qty=2)
		wo = self.make_submitted_work_order(plan, qty=2)

		data = self.run_report(plan.name)
		wo_row = self.get_work_order_row(data, "_Test FG Item")

		self.assertIsNotNone(wo_row)
		self.assertEqual(wo_row.get("document_name"), wo.name)
		self.assertEqual(wo_row.get("qty"), 2)
		self.assertEqual(wo_row.get("produced_qty"), 0)
		self.assertEqual(wo_row.get("pending_qty"), 2)

		summary = self.get_summary_row(data, "_Test FG Item")
		self.assertEqual(summary.get("qty"), 2)
		self.assertEqual(summary.get("produced_qty"), 0)

	def test_summary_reflects_produced_qty(self):
		"""Producing part of the work order updates produced and pending quantities."""
		plan = self.make_plan(planned_qty=2)
		wo = self.make_submitted_work_order(plan, qty=2)
		self.stock_required_materials(wo)

		se = frappe.get_doc(make_se_from_wo(wo.name, "Manufacture", 1))
		se.submit()

		data = self.run_report(plan.name)
		wo_row = self.get_work_order_row(data, "_Test FG Item")

		self.assertEqual(wo_row.get("document_name"), wo.name)
		self.assertEqual(wo_row.get("produced_qty"), 1)
		self.assertEqual(wo_row.get("pending_qty"), 1)

		summary = self.get_summary_row(data, "_Test FG Item")
		self.assertEqual(summary.get("qty"), 2)
		self.assertEqual(summary.get("produced_qty"), 1)
		self.assertEqual(summary.get("pending_qty"), 1)

	def test_summary_scoped_to_its_own_plan(self):
		"""Each plan's report only reports its own work order documents."""
		plan_a = self.make_plan(planned_qty=2)
		wo_a = self.make_submitted_work_order(plan_a, qty=2)

		plan_b = self.make_plan(planned_qty=3)
		wo_b = self.make_submitted_work_order(plan_b, qty=3)

		data_a = self.run_report(plan_a.name)
		document_names = {row.get("document_name") for row in data_a if row.get("document_name")}

		self.assertIn(wo_a.name, document_names)
		self.assertNotIn(wo_b.name, document_names)
