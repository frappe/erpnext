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

		project.load_tasks()

		task1 = project.tasks[0]
		self.assertEqual(task1.title, 'Task 1')
		self.assertEqual(task1.description, 'Task 1 description')
		self.assertEqual(getdate(task1.start_date), getdate('2019-01-01'))
		self.assertEqual(getdate(task1.end_date), getdate('2019-01-04'))

		self.assertEqual(len(project.tasks), 4)
		task4 = project.tasks[3]
		self.assertEqual(task4.title, 'Task 4')
		self.assertEqual(getdate(task4.end_date), getdate('2019-01-06'))

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