# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals
import frappe
import unittest
from frappe.utils import getdate, nowdate, add_days
from erpnext.projects.doctype.project.test_project import create_project
from erpnext.projects.doctype.task.task import CircularReferenceError

class TestTask(unittest.TestCase):
	def setUp(self):
		create_project()
		for task in ["_Test Task 1", "_Test Task 2", "_Test Task 3", "_Test Task 4", "Testing Overdue"]:
			create_task(task_name = task)

	def test_circular_reference(self):
		task1 = frappe.get_doc('Task', '_Test Task 1')
		task2 = frappe.get_doc('Task', '_Test Task 2')
		task2.append("depends_on", {"task": task1.name})
		task2.save()

		task3 = frappe.get_doc('Task', '_Test Task 3')
		task3.append("depends_on", {"task": task2.name})
		task3.save()
		
		task1.append("depends_on", {"task": task3.name})

		self.assertRaises(CircularReferenceError, task1.save)

		task1.set("depends_on", [])
		task1.save()

		task4 = frappe.get_doc('Task', '_Test Task 4')
		task4.append("depends_on", {"task": task1.name})
		task4.save()

		task3.append("depends_on", {"task": task4.name})

	def test_reschedule_dependent_task(self):
		task1 = frappe.get_doc('Task', '_Test Task 1')
		task2 = frappe.get_doc('Task', '_Test Task 2')
		task2.append("depends_on",
			{
				"task": task1.name,
				"project": "_Test Project"
			}
		)
		task2.save()
		task3 = frappe.get_doc('Task', '_Test Task 3')
		task3.append("depends_on",
			{
				"task": task2.name,
				"project": "_Test Project"
			}
		)
		task3.save()

		task1.exp_end_date = "2015-1-20"
		task1.save()

		self.assertEqual(frappe.db.get_value("Task", task2.name, "exp_start_date"), getdate('2015-1-21'))
		self.assertEqual(frappe.db.get_value("Task", task2.name, "exp_end_date"), getdate('2015-1-25'))

		self.assertEqual(frappe.db.get_value("Task", task3.name, "exp_start_date"), getdate('2015-1-26'))
		self.assertEqual(frappe.db.get_value("Task", task3.name, "exp_end_date"), getdate('2015-1-28'))

	def test_close_assignment(self):
		task = frappe.new_doc("Task")
		task.subject = "Test Close Assignment"
		task.insert()

		def assign():
			from frappe.desk.form import assign_to
			assign_to.add({
				"assign_to": "test@example.com",
				"doctype": task.doctype,
				"name": task.name,
				"description": "Close this task"
			})

		def get_owner_and_status():
			return frappe.db.get_value("ToDo", filters={"reference_type": task.doctype, "reference_name": task.name,
					"description": "Close this task"}, fieldname=("owner", "status"), as_dict=True)

		assign()
		todo = get_owner_and_status()
		self.assertEquals(todo.owner, "test@example.com")
		self.assertEquals(todo.status, "Open")

		# assignment should be
		task.load_from_db()
		task.status = "Closed"
		task.save()
		todo = get_owner_and_status()
		self.assertEquals(todo.owner, "test@example.com")
		self.assertEquals(todo.status, "Closed")

	def test_overdue(self):
		task = frappe.get_doc('Task', 'Testing Overdue')
		from erpnext.projects.doctype.task.task import set_tasks_as_overdue
		set_tasks_as_overdue()

		self.assertEquals(frappe.db.get_value("Task", task.name, "status"), "Overdue")

def create_task(task_name):
	if not frappe.db.exists("Task", task_name):
		task = frappe.get_doc({
			"doctype":"Task",
			"subject": task_name,
			"status": "Open",
			"exp_end_date": add_days(nowdate(), -1)
		})
		task.insert()