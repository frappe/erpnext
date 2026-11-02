# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
from erpnext.manufacturing.doctype.work_order.mapper import make_stock_entry
from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry import test_stock_entry
from erpnext.tests.utils import ERPNextTestSuite

STORES = "_Test Warehouse - _TC"


class TestWorkOrdersInProgress(ERPNextTestSuite):
	def work_orders_in_progress(self):
		report = frappe.get_file_json(
			frappe.get_app_path(
				"erpnext",
				"manufacturing",
				"report",
				"work_orders_in_progress",
				"work_orders_in_progress.json",
			)
		)
		return {row[0] for row in frappe.db.sql(report["query"])}

	def test_completed_work_order_with_process_loss_is_not_in_progress(self):
		material = make_item(properties={"is_stock_item": 1, "valuation_rate": 10}).name
		fg_item = make_item(properties={"is_stock_item": 1}).name
		bom = make_bom(item=fg_item, raw_materials=[material])
		test_stock_entry.make_stock_entry(item_code=material, target=STORES, qty=4, basic_rate=10)
		in_progress, finished = (
			make_wo_order_test_record(
				item=fg_item, bom_no=bom.name, qty=2, source_warehouse=STORES, skip_transfer=1
			)
			for _ in range(2)
		)
		frappe.get_doc(make_stock_entry(in_progress.name, "Manufacture", 1)).submit()
		manufacture = frappe.get_doc(make_stock_entry(finished.name, "Manufacture", 2))
		for row in manufacture.items:
			if row.is_finished_item:
				row.qty = 1
		manufacture.submit()
		finished.reload()
		self.assertEqual(
			(finished.status, finished.produced_qty, finished.process_loss_qty), ("Completed", 1, 1)
		)

		names = self.work_orders_in_progress()

		self.assertIn(in_progress.name, names)
		self.assertNotIn(finished.name, names)
