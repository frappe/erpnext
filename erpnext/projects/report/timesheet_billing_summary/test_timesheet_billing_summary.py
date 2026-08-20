# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe import _

from erpnext.projects.doctype.timesheet.test_timesheet import make_timesheet
from erpnext.projects.report.timesheet_billing_summary.timesheet_billing_summary import execute, group_by
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

	def execute_report(self, **extra):
		filters = frappe._dict({"company": "_Test Company", "employee": self.employee})
		filters.update(extra)
		return execute(filters)

	def run_report(self, **extra):
		return self.execute_report(**extra)[1]

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

	def test_report_summary_totals(self):
		self.make_ts(is_billable=1)
		self.make_ts(is_billable=1)

		_columns, data, _message, _chart, report_summary, _skip_total_row = self.execute_report()
		summary = {item["label"]: item["value"] for item in report_summary}

		self.assertFalse(any(row.get("timesheet") == "'Total'" for row in data))
		self.assertEqual(summary[_("Total Working Hours")], 4)
		self.assertEqual(summary[_("Total Billing Hours")], 4)
		self.assertEqual(summary[_("Total Billing Amount")], 200)

	def test_group_by_date_combines_entries_from_same_day(self):
		data = [
			frappe._dict(date="2026-08-20 09:00:00", hours=2, billing_hours=2, billing_amount=100),
			frappe._dict(date="2026-08-20 15:00:00", hours=3, billing_hours=3, billing_amount=150),
		]

		group_rows = [row for row in group_by(data, "date") if row.get("is_group")]

		self.assertEqual(len(group_rows), 1)
		self.assertEqual(group_rows[0]["hours"], 5)

	def test_report_summary_respects_project_user_permission(self):
		denied_project = frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": "_Test TBS Denied",
				"company": "_Test Company",
			}
		).insert()
		self.make_ts(is_billable=1)
		make_timesheet(
			self.employee,
			simulate=True,
			is_billable=1,
			project=denied_project.name,
		)

		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": "timesheet-summary@example.com",
				"first_name": "Timesheet Summary",
				"enabled": 1,
				"send_welcome_email": 0,
				"roles": [{"role": "Projects User"}, {"role": "Accounts User"}],
			}
		).insert(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": user.name,
				"allow": "Project",
				"for_value": self.project.name,
			}
		).insert(ignore_permissions=True)
		frappe.clear_cache(user=user.name)

		try:
			frappe.set_user(user.name)
			_columns, data, _message, _chart, report_summary, _skip_total_row = self.execute_report(
				group_by="project"
			)
		finally:
			frappe.set_user("Administrator")

		summary = {item["label"]: item["value"] for item in report_summary}
		group_projects = {row.get("project") for row in data if row.get("is_group")}
		self.assertEqual(group_projects, {self.project.name})
		self.assertEqual(summary[_("Total Working Hours")], 2)
		self.assertEqual(summary[_("Total Billing Hours")], 2)
		self.assertEqual(summary[_("Total Billing Amount")], 100)

	def test_draft_excluded_unless_requested(self):
		ts = make_timesheet(
			self.employee, simulate=True, is_billable=1, project=self.project.name, do_not_submit=True
		)

		# submitted-only by default: the draft timesheet is absent
		self.assertNotIn(ts.name, {r.get("timesheet") for r in self.run_report()})
		# ... but included when draft timesheets are requested
		self.assertIn(ts.name, {r.get("timesheet") for r in self.run_report(include_draft_timesheets=1)})
