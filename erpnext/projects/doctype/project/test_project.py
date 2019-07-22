# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals


import frappe, unittest
test_records = frappe.get_test_records('Project')
test_ignore = ["Sales Order"]

from erpnext.projects.doctype.project_template.test_project_template import get_project_template
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