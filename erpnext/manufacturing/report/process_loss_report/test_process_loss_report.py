# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import add_days, nowdate

from erpnext.manufacturing.doctype.work_order.mapper import make_stock_entry
from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
from erpnext.manufacturing.report.process_loss_report.process_loss_report import execute
from erpnext.stock.doctype.stock_entry import test_stock_entry
from erpnext.tests.utils import ERPNextTestSuite


class TestProcessLossReport(ERPNextTestSuite):
	def run_report(self, **extra):
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"from_date": nowdate(),
				"to_date": nowdate(),
			}
		)
		filters.update(extra)
		return execute(filters)[1]

	def find_row(self, data, work_order):
		for row in data:
			if row.get("name") == work_order:
				return row
		return None

	def make_manufactured_work_order(self, planned_qty, produced_qty, manufacture_qty=None):
		"""Create a submitted WO and manufacture `produced_qty` of `manufacture_qty` (default `planned_qty`).

		The difference is booked as process loss on the Manufacture stock entry,
		which propagates to the work order's `process_loss_qty`.
		"""
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

		self.make_manufacture(wo_order, manufacture_qty or planned_qty, produced_qty)
		wo_order.reload()
		return wo_order

	def make_manufacture(self, wo_order, qty, produced_qty, posting_date=None):
		manufacture = frappe.get_doc(make_stock_entry(wo_order.name, "Manufacture", qty))
		if posting_date:
			manufacture.set_posting_time = 1
			manufacture.posting_date = posting_date

		# Reduce the finished good qty below fg_completed_qty so the difference is
		# recorded as process loss.
		if qty != produced_qty:
			for d in manufacture.get("items"):
				if d.is_finished_item:
					d.qty = produced_qty
					d.transfer_qty = produced_qty * (d.conversion_factor or 1)
		manufacture.insert()
		manufacture.submit()

	def test_work_order_with_process_loss_is_listed(self):
		wo_order = self.make_manufactured_work_order(planned_qty=5, produced_qty=4)

		self.assertEqual(wo_order.process_loss_qty, 1)
		self.assertEqual(wo_order.produced_qty, 4)

		data = self.run_report()
		row = self.find_row(data, wo_order.name)

		self.assertIsNotNone(row, "Work order with process loss should appear in the report")
		self.assertEqual(row.production_item, "_Test FG Item")
		self.assertEqual(row.qty_to_manufacture, 5)
		self.assertEqual(row.produced_qty, 4)
		self.assertEqual(row.process_loss_qty, 1)

		# total_pl_value = process_loss_qty * (total_fg_value / (produced_qty + process_loss_qty))
		expected_pl_value = row.process_loss_qty * (row.total_fg_value / 5)
		self.assertAlmostEqual(row.total_pl_value, expected_pl_value)
		self.assertGreater(row.total_pl_value, 0)

	def test_process_loss_value_for_partial_production(self):
		wo_order = self.make_manufactured_work_order(planned_qty=10, produced_qty=4, manufacture_qty=5)

		row = self.find_row(self.run_report(), wo_order.name)
		self.assertEqual(row.qty_to_manufacture, 10)
		self.assertGreater(row.total_fg_value, 0)
		self.assertAlmostEqual(row.total_pl_value, row.total_fg_value / 5)

	def test_work_order_without_process_loss_is_not_listed(self):
		wo_order = self.make_manufactured_work_order(planned_qty=5, produced_qty=5)

		self.assertEqual(wo_order.process_loss_qty, 0)
		self.assertEqual(wo_order.produced_qty, 5)

		data = self.run_report()
		self.assertIsNone(
			self.find_row(data, wo_order.name),
			"Work order that produced the full planned qty should not appear (no loss)",
		)

	def test_item_filter_scopes_rows(self):
		wo_order = self.make_manufactured_work_order(planned_qty=5, produced_qty=4)

		# a matching production item includes the row, a non-matching one excludes it
		self.assertIsNotNone(self.find_row(self.run_report(item="_Test FG Item"), wo_order.name))
		self.assertIsNone(self.find_row(self.run_report(item="_Test FG Item 2"), wo_order.name))

	def test_work_order_filter_scopes_rows(self):
		wo_order = self.make_manufactured_work_order(planned_qty=5, produced_qty=4)

		# the matching work order is included, a different work order name is excluded
		self.assertIsNotNone(self.find_row(self.run_report(work_order=wo_order.name), wo_order.name))
		self.assertIsNone(self.find_row(self.run_report(work_order=f"{wo_order.name}-XX"), wo_order.name))

	def test_quantities_follow_the_report_dates(self):
		wo_order = self.make_manufactured_work_order(planned_qty=10, produced_qty=4, manufacture_qty=5)
		tomorrow = add_days(nowdate(), 1)
		self.make_manufacture(wo_order, qty=5, produced_qty=5, posting_date=tomorrow)

		today_row = self.find_row(self.run_report(), wo_order.name)
		self.assertEqual((today_row.produced_qty, today_row.process_loss_qty), (4, 1))

		both_days_row = self.find_row(self.run_report(to_date=tomorrow), wo_order.name)
		self.assertEqual((both_days_row.produced_qty, both_days_row.process_loss_qty), (9, 1))

		self.assertIsNone(self.find_row(self.run_report(from_date=tomorrow, to_date=tomorrow), wo_order.name))

	def test_process_loss_value_for_intermediate_operation(self):
		from erpnext.manufacturing.doctype.job_card.test_job_card import TestJobCard

		job_card_tests = TestJobCard()
		wo_order = job_card_tests.make_semi_fg_work_order("_Test PLR")
		job_card = job_card_tests.get_semi_fg_job_card(wo_order, "_Test PLR Op A")
		job_card.append(
			"time_logs",
			{"from_time": "2024-01-01 08:00:00", "to_time": "2024-01-01 09:00:00", "completed_qty": 3},
		)
		job_card.pending_qty = 0
		job_card.process_loss_qty = 2
		job_card.submit()
		frappe.get_doc(job_card.make_stock_entry_for_semi_fg_item()).submit()

		row = self.find_row(self.run_report(), wo_order.name)
		self.assertEqual((row.produced_qty, row.process_loss_qty), (0, 2))
		self.assertGreater(row.total_fg_value, 0)
		self.assertAlmostEqual(row.total_pl_value, row.total_fg_value * 2 / 5)
