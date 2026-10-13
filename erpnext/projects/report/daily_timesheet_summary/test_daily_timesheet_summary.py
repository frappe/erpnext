# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from datetime import timedelta

import frappe
from frappe.utils import get_datetime, today

from erpnext.projects.doctype.timesheet.test_timesheet import make_timesheet
from erpnext.projects.report.daily_timesheet_summary.daily_timesheet_summary import execute
from erpnext.setup.doctype.employee.test_employee import make_employee
from erpnext.tests.utils import ERPNextTestSuite


class TestDailyTimesheetSummary(ERPNextTestSuite):
	def test_submitted_timesheet_in_summary(self):
		timesheet = self.make_timesheet_logged_at(hour=9, hours=2)

		self.assertIn(timesheet.name, self.get_timesheets_of_today())

	def test_overnight_log_in_summary_of_its_start_day(self):
		timesheet = self.make_timesheet_logged_at(hour=22, hours=4)

		self.assertIn(timesheet.name, self.get_timesheets_of_today())

	def make_timesheet_logged_at(self, hour, hours):
		employee = make_employee("test_employee_6@salary.com", company="_Test Company")
		timesheet = make_timesheet(employee, simulate=True)
		start = get_datetime(today()) + timedelta(hours=hour)
		frappe.db.set_value(
			"Timesheet Detail",
			timesheet.time_logs[0].name,
			{"from_time": start, "to_time": start + timedelta(hours=hours)},
			update_modified=False,
		)
		return timesheet

	def get_timesheets_of_today(self):
		_columns, data = execute({"from_date": today(), "to_date": today()})
		return [row[0] for row in data]
