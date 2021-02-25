# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals
import frappe
import unittest
from six import string_types
from frappe.utils import getdate, nowdate, add_days

from erpnext.projects.doctype.task.task import CircularReferenceError

class TestTask(unittest.TestCase):
	def test_circular_reference(self):
		task1 = create_task("_Test Task 1", add_days(nowdate(), -15), add_days(nowdate(), -10))
		task2 = create_task("_Test Task 2", add_days(nowdate(), 11), add_days(nowdate(), 15), task1.name)
		task3 = create_task("_Test Task 3", add_days(nowdate(), 11), add_days(nowdate(), 15), task2.name)

		task1.reload()
		task1.append("depends_on", {
			"task": task3.name
		})

		self.assertRaises(CircularReferenceError, task1.save)

		task1.set("depends_on", [])
		task1.save()

		task4 = create_task("_Test Task 4", nowdate(), add_days(nowdate(), 15), task1.name)

		task3.append("depends_on", {
			"task": task4.name
		})

	def test_reschedule_dependent_task(self):
		project = frappe.get_value("Project", {"project_name": "_Test Project"})

		task1 = create_task("_Test Task 1", nowdate(), add_days(nowdate(), 10))

		task2 = create_task("_Test Task 2", add_days(nowdate(), 11), add_days(nowdate(), 15), task1.name)
		task2.get("depends_on")[0].project = project
		task2.save()

		task3 = create_task("_Test Task 3", add_days(nowdate(), 11), add_days(nowdate(), 15), task2.name)
		task3.get("depends_on")[0].project = project
		task3.save()

		task1.update({
			"exp_end_date": add_days(nowdate(), 20)
		})
		task1.save()

		self.assertEqual(frappe.db.get_value("Task", task2.name, "exp_start_date"),
			getdate(add_days(nowdate(), 21)))
		self.assertEqual(frappe.db.get_value("Task", task2.name, "exp_end_date"),
			getdate(add_days(nowdate(), 25)))

		self.assertEqual(frappe.db.get_value("Task", task3.name, "exp_start_date"),
			getdate(add_days(nowdate(), 26)))
		self.assertEqual(frappe.db.get_value("Task", task3.name, "exp_end_date"),
			getdate(add_days(nowdate(), 30)))

	def test_close_assignment(self):
		if not frappe.db.exists("Task", "Test Close Assignment"):
			task = frappe.new_doc("Task")
			task.subject = "Test Close Assignment"
			task.insert()

		def assign():
			from frappe.desk.form import assign_to
			assign_to.add({
				"assign_to": ["test@example.com"],
				"doctype": task.doctype,
				"name": task.name,
				"description": "Close this task"
			})

		def get_owner_and_status():
			return frappe.db.get_value("ToDo",
				filters={"reference_type": task.doctype, "reference_name": task.name,
					"description": "Close this task"},
				fieldname=("owner", "status"), as_dict=True)

		assign()
		todo = get_owner_and_status()
		self.assertEqual(todo.owner, "test@example.com")
		self.assertEqual(todo.status, "Open")

		# assignment should be
		task.load_from_db()
		task.status = "Completed"
		task.save()
		todo = get_owner_and_status()
		self.assertEqual(todo.owner, "test@example.com")
		self.assertEqual(todo.status, "Closed")

	def test_overdue(self):
		task = create_task("Testing Overdue", add_days(nowdate(), -10), add_days(nowdate(), -5))

		from erpnext.projects.doctype.task.task import set_tasks_as_overdue
		set_tasks_as_overdue()

		self.assertEqual(frappe.db.get_value("Task", task.name, "status"), "Overdue")

	def test_task_depends_on(self):
		task_1 = create_task("_Test Main Task 1")
		task_2 = create_task("_Test Main Task 2")
		task_3 = create_task("_Test Main Task 3")
		dependent = create_task("_Test Dependent Task", depends_on=[task_1.name, task_2.name])

		self.assertEqual(dependent.depends_on_tasks, "{0},{1}".format(task_1.name, task_2.name))

		# Add another task
		dependent.append("depends_on", {
			"task": task_3.name
		})
		dependent.save()
		self.assertEqual(dependent.depends_on_tasks, "{0},{1},{2}".format(task_1.name, task_2.name, task_3.name))

		# test remove doc
		frappe.delete_doc("Task Depends On", dependent.depends_on[2].name)
		dependent.load_from_db()
		
		# This will run validate
		dependent.save()

		self.assertEqual(dependent.depends_on_tasks, "{0},{1}".format(task_1.name, task_2.name))


def create_task(subject, start=None, end=None, depends_on=None, project=None, save=True):
	project = project or "_Test Project"
	
	if not frappe.db.exists("Project", project):
		project_doc = frappe.new_doc("Project")
		project_doc.project_name = project
		project_doc.status = "Open"
		project_doc.save()

	if not frappe.db.exists("Task", subject):
		task = frappe.new_doc('Task')
		task.status = "Open"
		task.subject = subject
		task.exp_start_date = start or nowdate()
		task.exp_end_date = end or nowdate()
		task.project = project or None if is_template else frappe.get_value("Project", {"project_name": "_Test Project"})
		task.is_template = is_template
		task.start = begin
		task.duration = duration
		task.is_group = is_group
		task.parent_task = parent_task
		if save:
			task.save()
	else:
		task = frappe.get_doc("Task", subject)

	if not depends_on:
		return task
	
	if isinstance(depends_on, string_types):
		depends_on = [depends_on]

	for task_name in depends_on:
		task.append("depends_on", {
			"task": task_name
		})

	if save:
		task.save()

	return task
