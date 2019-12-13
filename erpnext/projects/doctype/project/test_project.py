# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals


import frappe, unittest
test_records = frappe.get_test_records('Project')
test_ignore = ["Sales Order"]

from erpnext.projects.doctype.project_template.test_project_template import get_project_template, get_project_template_for_skipping_weekends
from erpnext.projects.doctype.project.project import set_project_status

from frappe.utils import getdate

class TestProject(unittest.TestCase):
	def test_project_with_template(self):
		frappe.db.sql('delete from tabTask where project = "Test Project with Template"')
		frappe.delete_doc('Project', 'Test Project with Template')

		project = get_project('Test Project with Template')

		tasks = frappe.get_all('Task', '*', dict(project=project.name), order_by='creation asc')

		task1 = tasks[0]
		self.assertEqual(task1.subject, 'Task 1')
		self.assertEqual(task1.description, 'Task 1 description')
		self.assertEqual(getdate(task1.exp_start_date), getdate('2019-01-01'))
		self.assertEqual(getdate(task1.exp_end_date), getdate('2019-01-04'))

		self.assertEqual(len(tasks), 4)
		task4 = tasks[3]
		self.assertEqual(task4.subject, 'Task 4')
		self.assertEqual(getdate(task4.exp_end_date), getdate('2019-01-06'))

	def test_project_with_template_and_skip_weekends(self):
		frappe.db.sql('delete from tabTask where project = "Test Project with Template and Skip Weekends"')
		frappe.delete_doc('Project', 'Test Project with Template and Skip Weekends')

		project = get_project('Test Project with Template and Skip Weekends')

		tasks = frappe.get_all('Task', '*', dict(project=project.name), order_by='creation asc')
		self.assertEqual(len(tasks), 4)

		task1 = tasks[0]
		self.assertEqual(task1.subject, 'Task 1')
		self.assertEqual(task1.description, 'Task 1 description')
		self.assertEqual(getdate(task1.exp_start_date), getdate('2019-12-11'))
		self.assertEqual(getdate(task1.exp_end_date), getdate('2019-12-12'))

		task2 = tasks[1]
		self.assertEqual(task2.subject, 'Task 2')
		self.assertEqual(task2.description, 'Task 2 description')
		self.assertEqual(getdate(task2.exp_start_date), getdate('2019-12-12'))
		self.assertEqual(getdate(task2.exp_end_date), getdate('2019-12-13'))

		task3 = tasks[2]
		self.assertEqual(task3.subject, 'Task 3')
		self.assertEqual(task3.description, 'Task 3 description')
		self.assertEqual(getdate(task3.exp_start_date), getdate('2019-12-12'))
		self.assertEqual(getdate(task3.exp_end_date), getdate('2019-12-14'))

		task4 = tasks[3]
		self.assertEqual(task4.subject, 'Task 4')
		self.assertEqual(task4.description, 'Task 4 description')
		self.assertEqual(getdate(task4.exp_start_date), getdate('2019-12-16'))
		self.assertEqual(getdate(task4.exp_end_date), getdate('2019-12-18'))

def get_project(name):
	template = get_project_template()

	project = frappe.get_doc(dict(
		doctype = 'Project',
		project_name = name,
		status = 'Open',
		project_template = template.name,
		expected_start_date = '2019-01-01'
	)).insert()

	return project

def get_project_for_skiping_weekends(name):
	template = get_project_template_for_skipping_weekends()

	project = frappe.get_doc(dict(
		doctype = 'Project',
		project_name = name,
		status = 'Open',
		project_template = template.name,
		expected_start_date = '2019-12-11'
	)).insert()
	
	return project
