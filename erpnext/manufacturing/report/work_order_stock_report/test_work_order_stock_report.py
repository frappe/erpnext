# Copyright (c) 2017, Velometro Mobility Inc and contributors
# For license information, please see license.txt

import frappe

from erpnext.tests.utils import ERPNextTestSuite


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
