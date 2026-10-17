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

	def test_disabled_template_is_refused_for_projects(self):
		template = make_project_template("_Test Disabled Project Template")
		template.db_set("disabled", 1)
		project = frappe.get_doc(
			doctype="Project",
			project_name="_Test Disabled Template Project",
			project_template=template.name,
			company="_Test Company",
		)
		self.assertRaises(frappe.ValidationError, project.insert)

	def test_template_tasks_are_validated(self):
		with self.subTest("task that is not a template"):
			task = create_task("_Test PT Live Task")
			template = frappe.get_doc(doctype="Project Template", name="_Test PT Live Task Template")
			template.append("tasks", {"task": task.name})
			self.assertRaises(frappe.ValidationError, template.insert)

		with self.subTest("child task that ends after its parent"):
			parent = create_task("_Test PT Phase", is_template=1, is_group=1, duration=2)
			child = create_task(
				"_Test PT Long Child", is_template=1, parent_task=parent.name, begin=1, duration=5
			)
			template = frappe.get_doc(doctype="Project Template", name="_Test PT Long Child Template")
			template.extend("tasks", [{"task": parent.name}, {"task": child.name}])
			self.assertRaises(frappe.ValidationError, template.insert)


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
