# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals


import frappe, unittest
test_records = frappe.get_test_records('Project')
test_ignore = ["Sales Order"]

from erpnext.projects.doctype.project_template.test_project_template import make_project_template
from erpnext.projects.doctype.project.project import set_project_status
from erpnext.projects.doctype.task.test_task import create_task
from frappe.utils import getdate, nowdate, add_days

class TestProject(unittest.TestCase):
	def test_project_with_template_having_no_parent_and_depend_tasks(self):
		""" 
		Test Action: Basic Test of a Project created from template. The template has a single task.
		"""
		frappe.db.sql('delete from tabTask where project = "Test Project with Templ - no parent and dependend tasks"')
		frappe.delete_doc('Project', 'Test Project with Templ - no parent and dependend tasks')

		task1 = task_exists("Test Temp Task with no parent and dependency")
		if not task1:
			task1 = create_task(subject="Test Temp Task with no parent and dependency", is_template=1, begin=5, duration=3)

		template = make_project_template("Test Project Template - no parent and dependend tasks", [task1])
		project = get_project("Test Project with Templ - no parent and dependend tasks", template)
		tasks = frappe.get_all('Task', '*', dict(project=project.name), order_by='creation asc')

		self.assertEqual(tasks[0].subject, 'Test Temp Task with no parent and dependency')
		self.assertEqual(getdate(tasks[0].exp_end_date), calculate_end_date(project, tasks[0]))
		self.assertEqual(len(tasks), 1)

	def test_project_template_having_parent_child_tasks(self):

		frappe.db.sql('delete from tabTask where project = "Test Project with Templ - tasks with parent-child"')
		frappe.delete_doc('Project', 'Test Project with Templ - tasks with parent-child')

		task1 = task_exists("Test Temp Task parent")
		if not task1:
			task1 = create_task(subject="Test Temp Task parent", is_group=1, is_template=1, begin=1, duration=1)

		task2 = task_exists("Test Temp Task child 1")
		if not task2:
			task2 = create_task(subject="Test Temp Task child 1", parent_task=task1.name, is_template=1, begin=1, duration=3)
		
		task3 = task_exists("Test Temp Task child 2")
		if not task3:
			task3 = create_task(subject="Test Temp Task child 2", parent_task=task1.name, is_template=1, begin=2, duration=3)

		template = make_project_template("Test Project Template  - tasks with parent-child", [task1, task2, task3])
		project = get_project("Test Project with Templ - tasks with parent-child", template)
		tasks = frappe.get_all('Task', '*', dict(project=project.name), order_by='creation asc')

		self.assertEqual(tasks[0].subject, 'Test Temp Task parent')
		self.assertEqual(getdate(tasks[0].exp_end_date), calculate_end_date(project, tasks[0]))

		self.assertEqual(tasks[1].subject, 'Test Temp Task child 1')
		self.assertEqual(getdate(tasks[1].exp_end_date), calculate_end_date(project, tasks[1]))
		self.assertEqual(tasks[1].parent_task, tasks[0].name)

		self.assertEqual(tasks[2].subject, 'Test Temp Task child 2')
		self.assertEqual(getdate(tasks[2].exp_end_date), calculate_end_date(project, tasks[2]))
		self.assertEqual(tasks[2].parent_task, tasks[0].name)

		self.assertEqual(len(tasks), 3)

	def test_project_template_having_dependent_tasks(self):

		frappe.db.sql('delete from tabTask where project = "Test Project with Templ - dependent tasks"')
		frappe.delete_doc('Project', 'Test Project with Templ - dependent tasks')

		task1 = task_exists("Test Temp Task for dependency")
		if not task1:
			task1 = create_task(subject="Test Temp Task for dependency", is_template=1, begin=3, duration=1)

		task2 = task_exists("Test Temp Task with dependency")
		if not task2:
			task2 = create_task(subject="Test Temp Task with dependency", depends_on=task1.name, is_template=1, begin=2, duration=2)
		
		template = make_project_template("Test Project with Templ - dependent tasks", [task1, task2])
		project = get_project("Test Project with Templ - dependent tasks", template)
		tasks = frappe.get_all('Task', '*', dict(project=project.name), order_by='creation asc')

		self.assertEqual(tasks[1].subject, 'Test Temp Task with dependency')
		self.assertEqual(getdate(tasks[1].exp_end_date), calculate_end_date(project, tasks[1]))
		self.assertTrue(tasks[1].depends_on_tasks.find(tasks[0].name) >= 0 )

		self.assertEqual(tasks[0].subject, 'Test Temp Task for dependency')
		self.assertEqual(getdate(tasks[0].exp_end_date), calculate_end_date(project, tasks[0]) )

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

	project = frappe.get_doc(dict(
		doctype = 'Project',
		project_name = args.project_name,
		status = 'Open',
		expected_start_date = args.start_date
	))

	if args.project_template_name:
		template = make_project_template(args.project_template_name)
		project.project_template = template.name

	if not frappe.db.exists("Project", args.project_name):
		project.insert()

	return project

def task_exists(subject):
	result = frappe.db.get_list("Task", filters={"subject": subject},fields=["name"])
	if not len(result):
		return False
	return frappe.get_doc("Task", result[0].name)

def calculate_end_date(project, task):
	return getdate(add_days(project.expected_start_date, task.start + task.duration))