# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import add_days, today

from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
from erpnext.manufacturing.report.work_order_summary.work_order_summary import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestWorkOrderSummary(ERPNextTestSuite):
	def run_report(self, **extra):
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"from_date": add_days(today(), -1),
				"to_date": today(),
			}
		)
		filters.update(extra)
		return execute(filters)[1]

	def test_work_order_appears_with_expected_fields(self):
		wo = make_wo_order_test_record(production_item="_Test FG Item", qty=10, company="_Test Company")

		rows = {row["name"]: row for row in self.run_report()}
		self.assertIn(wo.name, rows)

		row = rows[wo.name]
		self.assertEqual(row["production_item"], "_Test FG Item")
		self.assertEqual(row["qty"], 10)
		self.assertEqual(row["produced_qty"], 0)
		self.assertEqual(row["status"], "Not Started")

	def test_status_filter_excludes_other_statuses(self):
		wo = make_wo_order_test_record(production_item="_Test FG Item", qty=10, company="_Test Company")
		self.assertEqual(wo.status, "Not Started")

		# A "Completed" filter must not return a "Not Started" work order.
		names = {row["name"] for row in self.run_report(status="Completed")}
		self.assertNotIn(wo.name, names)

		# The matching status still returns it.
		names = {row["name"] for row in self.run_report(status="Not Started")}
		self.assertIn(wo.name, names)

	def test_date_range_excludes_work_order_outside_window(self):
		wo = make_wo_order_test_record(production_item="_Test FG Item", qty=10, company="_Test Company")

		# A window entirely in the past cannot contain a WO created today.
		names = {
			row["name"]
			for row in self.run_report(from_date=add_days(today(), -10), to_date=add_days(today(), -5))
		}
		self.assertNotIn(wo.name, names)

		# A window that includes today does contain it.
		names = {row["name"] for row in self.run_report()}
		self.assertIn(wo.name, names)

	def test_work_order_planned_for_later_is_listed(self):
		wo = make_wo_order_test_record(
			production_item="_Test FG Item",
			qty=10,
			company="_Test Company",
			planned_start_date=add_days(today(), 5),
		)

		rows = {row["name"]: row for row in self.run_report(to_date=add_days(today(), 30))}

		self.assertIn(wo.name, rows)
		self.assertEqual(rows[wo.name]["age"], 0)

	def test_work_order_ending_later_on_the_to_date_is_listed(self):
		wo = make_wo_order_test_record(
			production_item="_Test FG Item",
			qty=10,
			company="_Test Company",
			planned_start_date=f"{today()} 08:00:00",
		)
		wo.db_set("planned_end_date", f"{today()} 18:00:00")

		names = {row["name"] for row in self.run_report(based_on="Planned Date", from_date=today())}

		self.assertIn(wo.name, names)
