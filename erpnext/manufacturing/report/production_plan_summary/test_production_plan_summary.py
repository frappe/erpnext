# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase, change_settings

from erpnext.manufacturing.doctype.production_plan.test_production_plan import create_production_plan
from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry as make_se_from_wo
from erpnext.manufacturing.report.production_plan_summary.production_plan_summary import execute
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry


class TestProductionPlanSummary(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

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
		for item in wo.required_items:
			make_stock_entry(
				item_code=item.item_code,
				to_warehouse=item.source_warehouse or "_Test Warehouse - _TC",
				qty=item.required_qty + 10,
				rate=100,
			)

	def manufacture_with_one_lost(self, wo):
		self.stock_required_materials(wo)
		se = frappe.get_doc(make_se_from_wo(wo.name, "Manufacture", 2))
		for row in se.items:
			if row.is_finished_item:
				row.qty = 1
		se.submit()

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

	def test_process_loss_is_not_pending(self):
		plan = self.make_plan(planned_qty=2)
		wo = self.make_submitted_work_order(plan, qty=2)
		self.manufacture_with_one_lost(wo)
		wo.reload()
		self.assertEqual((wo.produced_qty, wo.process_loss_qty, wo.status), (1, 1, "Completed"))

		data = self.run_report(plan.name)

		self.assertEqual(self.get_work_order_row(data, "_Test FG Item").get("pending_qty"), 0)
		self.assertEqual(self.get_summary_row(data, "_Test FG Item").get("pending_qty"), 0)

	@change_settings("Manufacturing Settings", {"overproduction_percentage_for_work_order": 50})
	def test_replacement_work_order_for_lost_qty_is_not_negative(self):
		plan = self.make_plan(planned_qty=2)
		self.manufacture_with_one_lost(self.make_submitted_work_order(plan, qty=2))

		second = self.make_submitted_work_order(plan, qty=1)
		self.stock_required_materials(second)
		frappe.get_doc(make_se_from_wo(second.name, "Manufacture", 1)).submit()

		data = self.run_report(plan.name)

		self.assertEqual(
			[
				row.get("pending_qty")
				for row in data
				if row.get("item_code") == "_Test FG Item" and row.get("document_type") == "Work Order"
			],
			[0, 0],
		)
		self.assertEqual(self.get_summary_row(data, "_Test FG Item").get("pending_qty"), 0)

	def test_split_work_orders_with_lost_qty_leave_nothing_pending(self):
		plan = self.make_plan(planned_qty=4)
		self.manufacture_with_one_lost(self.make_submitted_work_order(plan, qty=2))

		second = self.make_submitted_work_order(plan, qty=2)
		self.stock_required_materials(second)
		frappe.get_doc(make_se_from_wo(second.name, "Manufacture", 2)).submit()

		data = self.run_report(plan.name)

		self.assertEqual(self.get_summary_row(data, "_Test FG Item").get("pending_qty"), 0)

	@change_settings("Manufacturing Settings", {"overproduction_percentage_for_work_order": 50})
	def test_replacement_work_order_keeps_lost_qty_pending(self):
		plan = self.make_plan(planned_qty=2)
		self.manufacture_with_one_lost(self.make_submitted_work_order(plan, qty=2))

		self.make_submitted_work_order(plan, qty=1)

		data = self.run_report(plan.name)

		self.assertEqual(self.get_summary_row(data, "_Test FG Item").get("pending_qty"), 1)

	def test_pending_qty_is_rounded_to_the_qty_precision(self):
		from erpnext.manufacturing.report.production_plan_summary.production_plan_summary import (
			get_pending_qty,
		)

		self.assertEqual(get_pending_qty(11.4, 11.2, 0.2), 0)
