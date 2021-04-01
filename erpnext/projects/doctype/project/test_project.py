# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals


import frappe, unittest
test_records = frappe.get_test_records('Project')
test_ignore = ["Sales Order"]

from erpnext.projects.doctype.project_template.test_project_template import make_project_template
from erpnext.projects.doctype.project.project import update_if_holiday
from erpnext.projects.doctype.task.test_task import create_task
from frappe.utils import getdate, nowdate, add_days

class TestProject(unittest.TestCase):
	def test_project_with_template_having_no_parent_and_depend_tasks(self):
		project_name = "Test Project with Template - No Parent and Dependend Tasks"
		frappe.db.sql(""" delete from tabTask where project = %s """, project_name)
		frappe.delete_doc('Project', project_name)

		task1 = task_exists("Test Template Task with No Parent and Dependency")
		if not task1:
			task1 = create_task(subject="Test Template Task with No Parent and Dependency", is_template=1, begin=5, duration=3)

		template = make_project_template("Test Project Template - No Parent and Dependend Tasks", [task1])
		project = get_project(project_name, template)
		tasks = frappe.get_all('Task', ['subject','exp_end_date','depends_on_tasks'], dict(project=project.name), order_by='creation asc')

		self.assertEqual(tasks[0].subject, 'Test Template Task with No Parent and Dependency')
		self.assertEqual(getdate(tasks[0].exp_end_date), calculate_end_date(project, 5, 3))
		self.assertEqual(len(tasks), 1)

	def test_project_template_having_parent_child_tasks(self):
		project_name = "Test Project with Template - Tasks with Parent-Child Relation"
		frappe.db.sql(""" delete from tabTask where project = %s """, project_name)
		frappe.delete_doc('Project', project_name)

		task1 = task_exists("Test Template Task Parent")
		if not task1:
			task1 = create_task(subject="Test Template Task Parent", is_group=1, is_template=1, begin=1, duration=4)

		task2 = task_exists("Test Template Task Child 1")
		if not task2:
			task2 = create_task(subject="Test Template Task Child 1", parent_task=task1.name, is_template=1, begin=1, duration=3)

		task3 = task_exists("Test Template Task Child 2")
		if not task3:
			task3 = create_task(subject="Test Template Task Child 2", parent_task=task1.name, is_template=1, begin=2, duration=3)

		template = make_project_template("Test Project Template  - Tasks with Parent-Child Relation", [task1, task2, task3])
		project = get_project(project_name, template)
		tasks = frappe.get_all('Task', ['subject','exp_end_date','depends_on_tasks', 'name', 'parent_task'], dict(project=project.name), order_by='creation asc')

		self.assertEqual(tasks[0].subject, 'Test Template Task Parent')
		self.assertEqual(getdate(tasks[0].exp_end_date), calculate_end_date(project, 1, 4))

		self.assertEqual(tasks[1].subject, 'Test Template Task Child 1')
		self.assertEqual(getdate(tasks[1].exp_end_date), calculate_end_date(project, 1, 3))
		self.assertEqual(tasks[1].parent_task, tasks[0].name)

		self.assertEqual(tasks[2].subject, 'Test Template Task Child 2')
		self.assertEqual(getdate(tasks[2].exp_end_date), calculate_end_date(project, 2, 3))
		self.assertEqual(tasks[2].parent_task, tasks[0].name)

		self.assertEqual(len(tasks), 3)

	def test_project_template_having_dependent_tasks(self):
		project_name = "Test Project with Template - Dependent Tasks"
		frappe.db.sql(""" delete from tabTask where project = %s  """, project_name)
		frappe.delete_doc('Project', project_name)

		task1 = task_exists("Test Template Task for Dependency")
		if not task1:
			task1 = create_task(subject="Test Template Task for Dependency", is_template=1, begin=3, duration=1)

		task2 = task_exists("Test Template Task with Dependency")
		if not task2:
			task2 = create_task(subject="Test Template Task with Dependency", depends_on=task1.name, is_template=1, begin=2, duration=2)

		template = make_project_template("Test Project with Template - Dependent Tasks", [task1, task2])
		project = get_project(project_name, template)
		tasks = frappe.get_all('Task', ['subject','exp_end_date','depends_on_tasks', 'name'], dict(project=project.name), order_by='creation asc')

		self.assertEqual(tasks[1].subject, 'Test Template Task with Dependency')
		self.assertEqual(getdate(tasks[1].exp_end_date), calculate_end_date(project, 2, 2))
		self.assertTrue(tasks[1].depends_on_tasks.find(tasks[0].name) >= 0 )

		self.assertEqual(tasks[0].subject, 'Test Template Task for Dependency')
		self.assertEqual(getdate(tasks[0].exp_end_date), calculate_end_date(project, 3, 1) )

		self.assertEqual(len(tasks), 2)

def get_project(name, template):

	project = frappe.get_doc(dict(
		doctype = 'Project',
		project_name = name,
		status = 'Open',
		project_template = template.name,
		expected_start_date = nowdate()
	)).insert()

	return project

def make_project(args):
	args = frappe._dict(args)

	if args.project_name and frappe.db.exists("Project", {"project_name": args.project_name}):
		return frappe.get_doc("Project", {"project_name": args.project_name})

	project = frappe.get_doc(dict(
		doctype = 'Project',
		project_name = args.project_name,
		status = 'Open',
		expected_start_date = args.start_date
	))

	if args.project_template_name:
		template = make_project_template(args.project_template_name)
		project.project_template = template.name

	project.insert()

	return project

def task_exists(subject):
	result = frappe.db.get_list("Task", filters={"subject": subject},fields=["name"])
	if not len(result):
		return False
	return frappe.get_doc("Task", result[0].name)

def calculate_end_date(project, start, duration):
	start = add_days(project.expected_start_date, start)
	start = update_if_holiday(project.holiday_list, start)
	end = add_days(start, duration)
	end = update_if_holiday(project.holiday_list, end)
	return getdate(end)