# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe import _
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.permissions import add_user_permission

from erpnext.projects.report.project_summary.project_summary import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestProjectSummary(ERPNextTestSuite):
	def make_project(self):
		return frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": f"_Test PS {frappe.generate_hash(length=6)}",
				"company": "_Test Company",
			}
		).insert()

	def make_task(self, project):
		return frappe.get_doc(
			{
				"doctype": "Task",
				"subject": f"Task {frappe.generate_hash(length=6)}",
				"project": project.name,
			}
		).insert()

	def test_restricted_user_sees_only_permitted_projects(self):
		permitted, other = self.make_project(), self.make_project()
		self.make_task(permitted)
		self.make_task(other)
		user = create_user("project_summary_restricted@example.com", "Projects User").name
		add_user_permission("Project", permitted.name, user)

		with self.set_user(user):
			_columns, data, _message, chart, report_summary = execute(frappe._dict())

		self.assertEqual([row.name for row in data], [permitted.name])
		self.assertEqual(chart["data"]["labels"], [permitted.project_name])
		summary = {s["label"]: s["value"] for s in report_summary}
		self.assertEqual(summary[_("Total Tasks")], 1)
