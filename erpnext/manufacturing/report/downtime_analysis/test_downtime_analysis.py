# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import frappe
from frappe.utils import add_days, get_datetime, today

from erpnext.manufacturing.doctype.workstation.test_workstation import make_workstation
from erpnext.manufacturing.report.downtime_analysis.downtime_analysis import execute
from erpnext.setup.doctype.employee.test_employee import make_employee
from erpnext.tests.utils import ERPNextTestSuite


class TestDowntimeAnalysis(ERPNextTestSuite):
	def setUp(self):
		self.workstation = make_workstation(workstation="_Test Downtime Workstation").name
		self.other_workstation = make_workstation(workstation="_Test Downtime Workstation 2").name
		self.operator = make_employee("test_downtime_operator@example.com", company="_Test Company")

		# from_time / to_time are two hours apart -> downtime of 120 minutes (2 hours).
		self.from_time = get_datetime(f"{today()} 09:00:00")
		self.to_time = get_datetime(f"{today()} 11:00:00")
		self.entry = self.make_downtime_entry(self.workstation)

	def make_downtime_entry(self, workstation, **extra):
		values = {
			"doctype": "Downtime Entry",
			"workstation": workstation,
			"operator": self.operator,
			"from_time": self.from_time,
			"to_time": self.to_time,
			"stop_reason": "Machine malfunction",
		}
		values.update(extra)
		return frappe.get_doc(values).insert()

	def run_report(self, **extra):
		filters = frappe._dict(
			{
				"from_date": add_days(today(), -1),
				"to_date": add_days(today(), 1),
			}
		)
		filters.update(extra)
		return execute(filters)[1]

	def row_for_entry(self, rows, name):
		return next((row for row in rows if row.get("name") == name), None)

	def test_downtime_is_computed_in_hours(self):
		# validate() stores downtime in minutes; the report converts it to hours.
		self.assertEqual(self.entry.downtime, 120)

		row = self.row_for_entry(self.run_report(), self.entry.name)
		self.assertIsNotNone(row, "Downtime Entry not present in report output")
		self.assertEqual(row.get("workstation"), self.workstation)
		self.assertEqual(row.get("operator"), self.operator)
		self.assertEqual(row.get("stop_reason"), "Machine malfunction")
		self.assertEqual(row.get("downtime"), 2.0)

	def test_workstation_filter_scopes_rows(self):
		other = self.make_downtime_entry(self.other_workstation)

		rows = self.run_report(workstation=self.workstation)
		names = {row.get("name") for row in rows}
		self.assertIn(self.entry.name, names)
		self.assertNotIn(other.name, names)
		self.assertTrue(all(row.get("workstation") == self.workstation for row in rows))

	def test_date_range_excludes_out_of_window_entries(self):
		# The report filters from_time >= from_date and to_time <= to_date; a window
		# ending before the entry's from_time must exclude it.
		rows = self.run_report(from_date=add_days(today(), -10), to_date=add_days(today(), -5))
		self.assertIsNone(self.row_for_entry(rows, self.entry.name))

	def test_chart_aggregates_downtime_per_workstation(self):
		self.make_downtime_entry(self.workstation)

		chart = execute(
			frappe._dict(
				{
					"from_date": add_days(today(), -1),
					"to_date": add_days(today(), 1),
					"workstation": self.workstation,
				}
			)
		)[3]

		self.assertIn(self.workstation, chart["data"]["labels"])
		index = chart["data"]["labels"].index(self.workstation)
		# Two entries of 2 hours each for this workstation -> 4 hours aggregated.
		self.assertEqual(chart["data"]["datasets"][0]["values"][index], 4.0)
