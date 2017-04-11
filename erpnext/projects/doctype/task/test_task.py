# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals
import frappe
import unittest
from frappe.utils import getdate, nowdate, add_days

# test_records = frappe.get_test_records('Task')

from erpnext.projects.doctype.task.task import CircularReferenceError

class TestTask(unittest.TestCase):
	def test_circular_reference(self):

		task1 =  frappe.new_doc('Task')
		task1.update({
			"status": "Open",
			"subject": "_Test Task 1",
			"project": "_Test Project",
			"exp_start_date": "2015-1-1",
			"exp_end_date": "2015-1-10"
		})
		task1.save()

		task2 =  frappe.new_doc('Task')
		task2.update({
			"status": "Open",
			"subject": "_Test Task 2",
			"project": "_Test Project",
			"exp_start_date": "2015-1-11",
			"exp_end_date": "2015-1-15",
			"depends_on":[
				{
					"task": task1.name
				}
			]
		})
		task2.save()

		task3 =  frappe.new_doc('Task')
		task3.update({
			"status": "Open",
			"subject": "_Test Task 2",
			"project": "_Test Project",
			"exp_start_date": "2015-1-11",
			"exp_end_date": "2015-1-15",
			"depends_on":[
				{
					"task": task2.name
				}
			]
		})
		task3.save()

		task1.append("depends_on", {
			"task": task3.name
		})
		self.assertRaises(CircularReferenceError, task1.save)

		task1.set("depends_on", [])
		task1.save()

		task4 =  frappe.new_doc('Task')
		task4.update({
			"status": "Open",
			"subject": "_Test Task 1",
			"exp_start_date": "2015-1-1",
			"exp_end_date": "2015-1-15",
			"depends_on":[
				{
					"task": task1.name
				}
			]
		})
		task4.save()

		task3.append("depends_on", {
			"task": task4.name
		})

	def test_reschedule_dependent_task(self):
		task1 =  frappe.new_doc('Task')
		task1.update({
			"status": "Open",
			"subject": "_Test Task 1",
			"project": "_Test Project",
			"exp_start_date": "2015-1-1",
			"exp_end_date": "2015-1-10"
		})
		task1.save()

		task2 =  frappe.new_doc('Task')
		task2.update({
			"status": "Open",
			"subject": "_Test Task 2",
			"project": "_Test Project",
			"exp_start_date": "2015-1-11",
			"exp_end_date": "2015-1-15",
			"depends_on":[
				{
					"task": task1.name,
					"project": "_Test Project"
				}
			]
		})
		task2.save()

		task3 =  frappe.new_doc('Task')
		task3.update({
			"status": "Open",
			"subject": "_Test Task 3",
			"project": "_Test Project",
			"exp_start_date": "2015-1-16",
			"exp_end_date": "2015-1-18",
			"depends_on":[
				{
					"task": task2.name,
					"project": "_Test Project"
				}
			]
		})
		task3.save()

		task1.update({
			"exp_end_date": "2015-1-20"
		})
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
		task = frappe.get_doc({
			"doctype":"Task",
			"subject": "Testing Overdue",
			"status": "Open",
			"exp_end_date": add_days(nowdate(), -1)
		})

		task.insert()

		from erpnext.projects.doctype.task.task import set_tasks_as_overdue
		set_tasks_as_overdue()

		self.assertEquals(frappe.db.get_value("Task", task.name, "status"), "Overdue")
