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
		"""Create a Work Order and manufacture a quantity with optional process loss."""
		manufacture_qty = manufacture_qty or planned_qty
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

		manufacture = frappe.get_doc(make_stock_entry(wo_order.name, "Manufacture", manufacture_qty))
		# Reduce the finished good qty below fg_completed_qty so the difference is
		# recorded as process loss.
		process_loss_qty = manufacture_qty - produced_qty
		if process_loss_qty:
			for d in manufacture.get("items"):
				if d.is_finished_item:
					d.qty = produced_qty
					d.transfer_qty = produced_qty * (d.conversion_factor or 1)
		manufacture.insert()
		manufacture.submit()

		wo_order.reload()
		return wo_order

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

		# Five units were processed, including one unit of process loss.
		expected_pl_value = row.process_loss_qty * (row.total_fg_value / 5)
		self.assertAlmostEqual(row.total_pl_value, expected_pl_value)
		self.assertGreater(row.total_pl_value, 0)

	def test_process_loss_value_for_partial_production(self):
		work_order = self.make_manufactured_work_order(planned_qty=10, produced_qty=4, manufacture_qty=5)
		row = self.find_row(self.run_report(work_order=work_order.name), work_order.name)
		self.assertEqual(row.qty_to_manufacture, 10)
		self.assertAlmostEqual(row.total_pl_value, row.total_fg_value / 5)

	def test_quantities_match_the_date_range(self):
		work_order = self.make_manufactured_work_order(planned_qty=10, produced_qty=4, manufacture_qty=5)
		first_row = self.find_row(self.run_report(work_order=work_order.name), work_order.name)
		manufacture = frappe.get_doc(make_stock_entry(work_order.name, "Manufacture", 5))
		manufacture.set_posting_time = 1
		manufacture.posting_date = add_days(nowdate(), 1)
		for item in manufacture.items:
			if item.is_finished_item:
				item.qty = item.transfer_qty = 3
		manufacture.insert()
		manufacture.submit()

		row = self.find_row(self.run_report(work_order=work_order.name), work_order.name)
		self.assertEqual(row.produced_qty, 4)
		self.assertEqual(row.process_loss_qty, 1)
		self.assertEqual(row.total_fg_value, first_row.total_fg_value)
		self.assertEqual(row.total_pl_value, first_row.total_pl_value)

	def test_manufactured_quantity_excludes_semi_finished_goods(self):
		from erpnext.manufacturing.doctype.job_card.test_job_card import TestJobCard

		job_card_tests = TestJobCard()
		work_order = job_card_tests.make_semi_fg_work_order("_Test Process Loss Report", qty=10)
		for day, operation in enumerate(("A", "B"), start=1):
			job_card = job_card_tests.get_semi_fg_job_card(
				work_order, f"_Test Process Loss Report Op {operation}"
			)
			job_card.append(
				"time_logs",
				{
					"from_time": f"2024-01-0{day} 08:00:00",
					"to_time": f"2024-01-0{day} 09:00:00",
					"completed_qty": 8,
				},
			)
			job_card.pending_qty = 0
			job_card.process_loss_qty = 2
			job_card.submit()
			frappe.get_doc(job_card.make_stock_entry_for_semi_fg_item()).submit()

		row = self.find_row(self.run_report(work_order=work_order.name), work_order.name)
		self.assertEqual(row.produced_qty, 8)

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
