# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.projects.doctype.task.test_task import create_task
from erpnext.tests.utils import ERPNextTestSuite


class TestProjectTemplate(ERPNextTestSuite):
	def test_dependency_task_must_be_in_template(self):
		dependency = create_task("_Test PT Dependency", is_template=1)
		dependent = create_task("_Test PT Dependent", is_template=1, depends_on=dependency.name)

		template = frappe.get_doc(doctype="Project Template", name="_Test PT Missing Dependency")
		template.append("tasks", {"task": dependent.name})
		# the dependency task is not in the template's task list
		self.assertRaises(frappe.ValidationError, template.insert)

		# adding the dependency task makes the template valid
		template.append("tasks", {"task": dependency.name})
		template.insert()
		self.assertTrue(frappe.db.exists("Project Template", template.name))


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
