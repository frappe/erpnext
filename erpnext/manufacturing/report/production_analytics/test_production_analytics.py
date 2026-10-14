# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe import _
from frappe.utils import get_first_day, get_last_day, today

from erpnext.tests.utils import ERPNextTestSuite


class TestProductionAnalytics(ERPNextTestSuite):
	def run_report(self, **extra):
		from erpnext.manufacturing.report.production_analytics.production_analytics import execute

		filters = frappe._dict(
			{
				"company": "_Test Company",
				"from_date": get_first_day(today()),
				"to_date": get_last_day(today()),
				"range": "Monthly",
			}
		)
		filters.update(extra)
		columns, data, _msg, _chart = execute(filters)
		return columns, data

	def get_period_count(self, columns, data, status, period_label):
		"""Return the count for a status row under the period column resolved by label."""
		period_fieldname = next(col["fieldname"] for col in columns if col.get("label") == period_label)
		# the report stores the translated status label, so translate before matching
		row = next(row for row in data if row["status"] == _(status))
		return row[period_fieldname]

	def test_submitted_work_order_increments_status_count(self):
		from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record

		# pin the reporting window once so both runs use the same period even if the
		# test happens to straddle a month boundary
		from_date, to_date = get_first_day(today()), get_last_day(today())

		# The current month is the period a newly created Work Order falls into (bucketed by creation date).
		cols_before, data_before = self.run_report(from_date=from_date, to_date=to_date)
		period_label = cols_before[-1]["label"]
		before = self.get_period_count(cols_before, data_before, "Not Started", period_label)

		wo = make_wo_order_test_record(production_item="_Test FG Item", qty=10, company="_Test Company")
		self.assertEqual(wo.docstatus, 1)
		# A freshly submitted Work Order with no material transfer has status "Not Started".
		self.assertEqual(wo.status, "Not Started")

		cols_after, data_after = self.run_report(from_date=from_date, to_date=to_date)
		after = self.get_period_count(cols_after, data_after, "Not Started", period_label)

		self.assertEqual(after, before + 1)

	def test_report_shape(self):
		columns, data = self.run_report()

		# First column is the Status column, followed by one column per period.
		self.assertEqual(columns[0]["fieldname"], "status")
		self.assertGreaterEqual(len(columns), 2)

		# One row per known Work Order status.
		statuses = {row["status"] for row in data}
		for status in ("Not Started", "Overdue", "Pending", "Completed", "Closed", "Stopped"):
			self.assertIn(_(status), statuses)
