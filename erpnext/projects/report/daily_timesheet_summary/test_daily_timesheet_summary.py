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
		frappe.set_user("Administrator")

		employee = make_employee("test_employee_6@salary.com", company="_Test Company")
		timesheet = make_timesheet(employee, simulate=True)

		# make_timesheet logs at now_datetime(); run late in the day (under the site timezone)
		# the 2h log crosses midnight and falls outside the report's `to_time <= end-of-day`
		# bound. Pin the log to a fixed mid-day window on today so the assertion is
		# time-of-day independent.
		start = get_datetime(today()) + timedelta(hours=9)
		frappe.db.set_value(
			"Timesheet Detail",
			timesheet.time_logs[0].name,
			{"from_time": start, "to_time": start + timedelta(hours=2)},
			update_modified=False,
		)

		_columns, data = execute({"from_date": today(), "to_date": today()})

		# Row column order: [Timesheet.name, employee, employee_name, from_time, to_time,
		# hours, activity_type, task, project, status]. The converted join must surface the
		# submitted timesheet for today; row[0] holds the Timesheet name.
		names = [row[0] for row in data]
		self.assertIn(timesheet.name, names)
