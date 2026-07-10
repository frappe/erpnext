# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.projects.doctype.timesheet.test_timesheet import make_timesheet
from erpnext.projects.report.timesheet_billing_summary.timesheet_billing_summary import execute
from erpnext.setup.doctype.employee.test_employee import make_employee
from erpnext.tests.utils import ERPNextTestSuite


class TestTimesheetBillingSummary(ERPNextTestSuite):
	"""Lists submitted Timesheet Detail rows with working/billing hours and amount,
	optionally grouped by date/project/employee."""

	def setUp(self):
		self.employee = make_employee("timesheet_billing@example.com", company="_Test Company")
		self.project = frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": f"_Test TBS {frappe.generate_hash(length=6)}",
				"company": "_Test Company",
			}
		).insert()

	def make_ts(self, is_billable=1):
		return make_timesheet(
			self.employee, simulate=True, is_billable=is_billable, project=self.project.name
		)

	def run_report(self, **extra):
		filters = frappe._dict({"company": "_Test Company", "employee": self.employee})
		filters.update(extra)
		return execute(filters)[1]

	def test_billable_timesheet_row(self):
		ts = self.make_ts(is_billable=1)
		detail = ts.time_logs[0]

		rows = [r for r in self.run_report() if r.get("timesheet") == ts.name]
		self.assertTrue(rows, "Timesheet missing from report")
		row = rows[0]
		self.assertEqual(row["hours"], 2)
		self.assertEqual(row["billing_hours"], detail.billing_hours)
		self.assertEqual(row["billing_amount"], detail.billing_amount)
		self.assertEqual(row["project"], self.project.name)

	def test_group_by_project_sums_hours(self):
		self.make_ts(is_billable=1)

		data = self.run_report(group_by="project")
		group_rows = [r for r in data if r.get("is_group") and r.get("project") == self.project.name]
		self.assertTrue(group_rows, "Grouped project row missing")
		self.assertEqual(group_rows[0]["hours"], 2)

	def test_draft_excluded_unless_requested(self):
		ts = make_timesheet(
			self.employee, simulate=True, is_billable=1, project=self.project.name, do_not_submit=True
		)

		# submitted-only by default: the draft timesheet is absent
		self.assertNotIn(ts.name, {r.get("timesheet") for r in self.run_report()})
		# ... but included when draft timesheets are requested
		self.assertIn(ts.name, {r.get("timesheet") for r in self.run_report(include_draft_timesheets=1)})
