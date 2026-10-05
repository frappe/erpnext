# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import unittest

import frappe
from frappe.core.doctype.user_permission.test_user_permission import create_user

from erpnext.projects.doctype.task.test_task import create_task
from erpnext.tests.utils import ERPNextTestSuite


class TestProjectTemplate(ERPNextTestSuite):
	def test_projects_manager_maintains_and_projects_user_reads_templates(self):
		manager = create_user("project_template_manager@example.com", "Projects Manager").name
		user = create_user("project_template_user@example.com", "Projects User").name

		for ptype in ("create", "read", "write"):
			self.assertTrue(frappe.has_permission("Project Template", ptype, user=manager))
		self.assertTrue(frappe.has_permission("Project Template", "read", user=user))
		self.assertFalse(frappe.has_permission("Project Template", "write", user=user))


def make_project_template(project_template_name, project_tasks=None):
	if project_tasks is None:
		project_tasks = []
	if not frappe.db.exists("Project Template", project_template_name):
		project_tasks = project_tasks or [
			create_task(subject="_Test Template Task 1", is_template=1, begin=0, duration=3),
			create_task(subject="_Test Template Task 2", is_template=1, begin=0, duration=2),
		]
		doc = frappe.get_doc(doctype="Project Template", name=project_template_name)
		for task in project_tasks:
			doc.append("tasks", {"task": task.name})
		doc.insert()

	return frappe.get_doc("Project Template", project_template_name)
