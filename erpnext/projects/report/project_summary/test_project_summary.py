# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe import _

from erpnext.projects.report.project_summary.project_summary import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestProjectSummary(ERPNextTestSuite):
	"""Lists projects with their total / completed / overdue task counts."""

	def make_project(self):
		return frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": f"_Test PS {frappe.generate_hash(length=6)}",
				"company": "_Test Company",
			}
		).insert()

	def make_task(self, project, status="Open"):
		task = frappe.get_doc(
			{
				"doctype": "Task",
				"subject": f"Task {frappe.generate_hash(length=6)}",
				"project": project.name,
			}
		).insert()
		if status != "Open":
			# set the status directly; the report counts tasks by their stored status
			frappe.db.set_value("Task", task.name, "status", status)
		return task

	def run_report(self, project):
		return execute(frappe._dict({"name": project.name}))

	def project_row(self, project):
		_columns, data, *_rest = self.run_report(project)
		return next((r for r in data if r["name"] == project.name), None)

	def test_task_counts(self):
		project = self.make_project()
		self.make_task(project, "Completed")
		self.make_task(project, "Completed")
		self.make_task(project, "Open")
		self.make_task(project, "Overdue")

		row = self.project_row(project)
		self.assertIsNotNone(row, "Project missing from report")
		self.assertEqual(row["total_tasks"], 4)
		self.assertEqual(row["completed_tasks"], 2)
		self.assertEqual(row["overdue_tasks"], 1)

	def test_report_summary_totals(self):
		project = self.make_project()
		self.make_task(project, "Completed")
		self.make_task(project, "Open")

		_columns, _data, _message, _chart, report_summary = self.run_report(project)
		summary = {s["label"]: s["value"] for s in report_summary}
		self.assertEqual(summary[_("Total Tasks")], 2)
		self.assertEqual(summary[_("Completed Tasks")], 1)
		self.assertEqual(summary[_("Overdue Tasks")], 0)
