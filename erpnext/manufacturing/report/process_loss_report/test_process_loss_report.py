# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import add_days, nowdate

from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry
from erpnext.manufacturing.report.process_loss_report.process_loss_report import execute
from erpnext.stock.doctype.stock_entry import test_stock_entry
from erpnext.tests.utils import ERPNextTestSuite


class TestProcessLossReport(ERPNextTestSuite):
	def run_report(self, **extra):
		filters = frappe._dict({"company": "_Test Company", "from_date": nowdate(), "to_date": nowdate()})
		filters.update(extra)
		return execute(filters)[1]

	def find_row(self, data, work_order):
		return next((row for row in data if row.get("name") == work_order), None)

	def make_manufactured_work_order(self, planned_qty, produced_qty, manufacture_qty):
		wo_order = make_wo_order_test_record(production_item="_Test FG Item", qty=planned_qty)

		test_stock_entry.make_stock_entry(
			item_code="_Test Item", target="Stores - _TC", qty=100, basic_rate=100
		)
		test_stock_entry.make_stock_entry(
			item_code="_Test Item Home Desktop 100", target="Stores - _TC", qty=100, basic_rate=100
		)

		transfer = frappe.get_doc(
			make_stock_entry(wo_order.name, "Material Transfer for Manufacture", planned_qty)
		)
		for d in transfer.get("items"):
			d.s_warehouse = "Stores - _TC"
		transfer.insert()
		transfer.submit()

		self.make_manufacture(wo_order, manufacture_qty, produced_qty)
		return wo_order

	def make_manufacture(self, wo_order, qty, produced_qty, posting_date=None):
		manufacture = frappe.get_doc(make_stock_entry(wo_order.name, "Manufacture", qty))
		if posting_date:
			manufacture.set_posting_time = 1
			manufacture.posting_date = posting_date

		if qty != produced_qty:
			for d in manufacture.get("items"):
				if d.is_finished_item:
					d.qty = produced_qty
					d.transfer_qty = produced_qty * (d.conversion_factor or 1)
		manufacture.insert()
		manufacture.submit()

	def test_quantities_follow_the_report_dates(self):
		wo_order = self.make_manufactured_work_order(planned_qty=10, produced_qty=4, manufacture_qty=5)
		tomorrow = add_days(nowdate(), 1)
		self.make_manufacture(wo_order, qty=5, produced_qty=5, posting_date=tomorrow)

		today_row = self.find_row(self.run_report(), wo_order.name)
		self.assertEqual((today_row.produced_qty, today_row.process_loss_qty), (4, 1))

		both_days_row = self.find_row(self.run_report(to_date=tomorrow), wo_order.name)
		self.assertEqual((both_days_row.produced_qty, both_days_row.process_loss_qty), (9, 1))

		self.assertIsNone(self.find_row(self.run_report(from_date=tomorrow, to_date=tomorrow), wo_order.name))

	def test_process_loss_value_for_partial_production(self):
		wo_order = self.make_manufactured_work_order(planned_qty=10, produced_qty=4, manufacture_qty=5)

		row = self.find_row(self.run_report(), wo_order.name)
		self.assertEqual(row.qty_to_manufacture, 10)
		self.assertGreater(row.total_fg_value, 0)
		self.assertAlmostEqual(row.total_pl_value, row.total_fg_value / 5)
