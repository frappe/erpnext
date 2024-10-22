# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase
from frappe.utils import add_days, getdate, nowdate

from erpnext.projects.doctype.project_template.test_project_template import make_project_template
from erpnext.projects.doctype.task.test_task import create_task
from erpnext.selling.doctype.sales_order.sales_order import make_project as make_project_from_so
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

IGNORE_TEST_RECORD_DEPENDENCIES = ["Sales Order"]


class UnitTestProject(UnitTestCase):
	"""
	Unit tests for Project.
	Use this class for testing individual functions and methods.
	"""

	pass


class TestProject(IntegrationTestCase):
	def test_project_with_template_having_no_parent_and_depend_tasks(self):
		project_name = "Test Project with Template - No Parent and Dependend Tasks"
		frappe.db.sql(""" delete from tabTask where project = %s """, project_name)
		frappe.delete_doc("Project", project_name)

		task1 = task_exists("Test Template Task with No Parent and Dependency")
		if not task1:
			task1 = create_task(
				subject="Test Template Task with No Parent and Dependency",
				is_template=1,
				begin=5,
				duration=3,
				priority="High",
			)

		template = make_project_template("Test Project Template - No Parent and Dependend Tasks", [task1])
		project = get_project(project_name, template)
		tasks = frappe.get_all(
			"Task",
			["subject", "exp_end_date", "depends_on_tasks", "priority"],
			dict(project=project.name),
			order_by="creation asc",
		)

		self.assertEqual(tasks[0].priority, "High")
		self.assertEqual(tasks[0].subject, "Test Template Task with No Parent and Dependency")
		self.assertEqual(getdate(tasks[0].exp_end_date), calculate_end_date(project, 5, 3))
		self.assertEqual(len(tasks), 1)

	def test_project_template_having_parent_child_tasks(self):
		project_name = "Test Project with Template - Tasks with Parent-Child Relation"

		if frappe.db.get_value("Project", {"project_name": project_name}, "name"):
			project_name = frappe.db.get_value("Project", {"project_name": project_name}, "name")

		frappe.db.sql(""" delete from tabTask where project = %s """, project_name)
		frappe.delete_doc("Project", project_name)

		task1 = task_exists("Test Template Task Parent")
		if not task1:
			task1 = create_task(
				subject="Test Template Task Parent", is_group=1, is_template=1, begin=1, duration=10
			)

		task2 = task_exists("Test Template Task Child 1")
		if not task2:
			task2 = create_task(
				subject="Test Template Task Child 1",
				parent_task=task1.name,
				is_template=1,
				begin=1,
				duration=3,
			)

		task3 = task_exists("Test Template Task Child 2")
		if not task3:
			task3 = create_task(
				subject="Test Template Task Child 2",
				parent_task=task1.name,
				is_template=1,
				begin=2,
				duration=3,
			)

		template = make_project_template(
			"Test Project Template  - Tasks with Parent-Child Relation", [task1, task2, task3]
		)
		project = get_project(project_name, template)
		tasks = frappe.get_all(
			"Task",
			["subject", "exp_end_date", "depends_on_tasks", "name", "parent_task"],
			dict(project=project.name),
			order_by="creation asc",
		)

		self.assertEqual(tasks[0].subject, "Test Template Task Parent")
		self.assertEqual(getdate(tasks[0].exp_end_date), calculate_end_date(project, 1, 10))

		self.assertEqual(tasks[1].subject, "Test Template Task Child 1")
		self.assertEqual(getdate(tasks[1].exp_end_date), calculate_end_date(project, 1, 3))
		self.assertEqual(tasks[1].parent_task, tasks[0].name)

		self.assertEqual(tasks[2].subject, "Test Template Task Child 2")
		self.assertEqual(getdate(tasks[2].exp_end_date), calculate_end_date(project, 2, 3))
		self.assertEqual(tasks[2].parent_task, tasks[0].name)

		self.assertEqual(len(tasks), 3)

	def test_project_template_having_dependent_tasks(self):
		project_name = "Test Project with Template - Dependent Tasks"
		frappe.db.sql(""" delete from tabTask where project = %s  """, project_name)
		frappe.delete_doc("Project", project_name)

		task1 = task_exists("Test Template Task for Dependency")
		if not task1:
			task1 = create_task(
				subject="Test Template Task for Dependency", is_template=1, begin=3, duration=1
			)

		task2 = task_exists("Test Template Task with Dependency")
		if not task2:
			task2 = create_task(
				subject="Test Template Task with Dependency",
				depends_on=task1.name,
				is_template=1,
				begin=2,
				duration=2,
			)

		template = make_project_template("Test Project with Template - Dependent Tasks", [task1, task2])
		project = get_project(project_name, template)
		tasks = frappe.get_all(
			"Task",
			["subject", "exp_end_date", "depends_on_tasks", "name"],
			dict(project=project.name),
			order_by="creation asc",
		)

		self.assertEqual(tasks[1].subject, "Test Template Task with Dependency")
		self.assertEqual(getdate(tasks[1].exp_end_date), calculate_end_date(project, 2, 2))
		self.assertTrue(tasks[1].depends_on_tasks.find(tasks[0].name) >= 0)

		self.assertEqual(tasks[0].subject, "Test Template Task for Dependency")
		self.assertEqual(getdate(tasks[0].exp_end_date), calculate_end_date(project, 3, 1))

		self.assertEqual(len(tasks), 2)

	def test_project_linking_with_sales_order(self):
		so = make_sales_order()
		project = make_project_from_so(so.name)

		project.save()
		self.assertEqual(project.sales_order, so.name)

		so.reload()
		self.assertEqual(so.project, project.name)

		project.delete()

		so.reload()
		self.assertFalse(so.project)

	def test_project_with_template_tasks_having_common_name(self):
		# Step - 1: Create Template Parent Tasks
		template_parent_task1 = create_task(subject="Parent Task - 1", is_template=1, is_group=1)
		template_parent_task2 = create_task(subject="Parent Task - 2", is_template=1, is_group=1)
		template_parent_task3 = create_task(subject="Parent Task - 1", is_template=1, is_group=1)

		# Step - 2: Create Template Child Tasks
		template_task1 = create_task(
			subject="Task - 1", is_template=1, parent_task=template_parent_task1.name
		)
		template_task2 = create_task(
			subject="Task - 2", is_template=1, parent_task=template_parent_task2.name
		)
		template_task3 = create_task(
			subject="Task - 1", is_template=1, parent_task=template_parent_task3.name
		)

		# Step - 3: Create Project Template
		template_tasks = [
			template_parent_task1,
			template_task1,
			template_parent_task2,
			template_task2,
			template_parent_task3,
			template_task3,
		]
		project_template = make_project_template("Project template with common Task Subject", template_tasks)

		# Step - 4: Create Project against the Project Template
		project = get_project("Project with common Task Subject", project_template)
		project_tasks = frappe.get_all(
			"Task", {"project": project.name}, ["subject", "parent_task", "is_group"]
		)

		# Test - 1: No. of Project Tasks should be equal to No. of Template Tasks
		self.assertEqual(len(project_tasks), len(template_tasks))

		# Test - 2: All child Project Tasks should have Parent Task linked
		for pt in project_tasks:
			if not pt.is_group:
				self.assertIsNotNone(pt.parent_task)

	def test_project_having_no_tasks_complete(self):
		project_name = "Test Project - No Tasks Completion"
		frappe.db.sql(""" delete from tabTask where project = %s """, project_name)
		frappe.delete_doc("Project", project_name)

		project = frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": project_name,
				"status": "Open",
				"expected_start_date": nowdate(),
				"company": "_Test Company",
			}
		).insert()

		tasks = frappe.get_all(
			"Task",
			["subject", "exp_end_date", "depends_on_tasks", "name", "parent_task"],
			dict(project=project.name),
			order_by="creation asc",
		)

		self.assertEqual(project.status, "Open")
		self.assertEqual(len(tasks), 0)
		project.status = "Completed"
		project.save()
		self.assertEqual(project.status, "Completed")


def get_project(name, template):
	project = frappe.get_doc(
		dict(
			doctype="Project",
			project_name=name,
			status="Open",
			project_template=template.name,
			expected_start_date=nowdate(),
			company="_Test Company",
		)
	).insert()

	return project


def make_project(args):
	args = frappe._dict(args)

	if args.project_name and frappe.db.exists("Project", {"project_name": args.project_name}):
		return frappe.get_doc("Project", {"project_name": args.project_name})

	project = frappe.get_doc(
		dict(
			doctype="Project",
			project_name=args.project_name,
			status="Open",
			expected_start_date=args.start_date,
			company=args.company or "_Test Company",
		)
	)

	if args.project_template_name:
		template = make_project_template(args.project_template_name)
		project.project_template = template.name

	project.insert()

	return project


def task_exists(subject):
	result = frappe.db.get_list("Task", filters={"subject": subject}, fields=["name"])
	if not len(result):
		return False
	return frappe.get_doc("Task", result[0].name)


def calculate_end_date(project, start, duration):
	start = add_days(project.expected_start_date, start)
	start = project.update_if_holiday(start)
	end = add_days(start, duration)
	end = project.update_if_holiday(end)
	return getdate(end)
