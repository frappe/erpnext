# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, nowdate

from erpnext.projects.doctype.task.task import (
	CircularReferenceError,
	ParentIsGroupError,
	set_tasks_as_overdue,
)


class TestTask(FrappeTestCase):
	def test_circular_reference(self):
		task1 = create_task("_Test Task 1", add_days(nowdate(), -15), add_days(nowdate(), -10))
		task2 = create_task("_Test Task 2", add_days(nowdate(), 11), add_days(nowdate(), 15), task1.name)
		task3 = create_task("_Test Task 3", add_days(nowdate(), 11), add_days(nowdate(), 15), task2.name)

		task1.reload()
		task1.append("depends_on", {"task": task3.name})

		self.assertRaises(CircularReferenceError, task1.save)

		task1.set("depends_on", [])
		task1.save()

		task4 = create_task("_Test Task 4", nowdate(), add_days(nowdate(), 15), task1.name)

		task3.append("depends_on", {"task": task4.name})

	def test_reschedule_dependent_task(self):
		task1 = create_task("_Test Task 1", nowdate(), add_days(nowdate(), 10))
		task2 = create_task("_Test Task 2", add_days(nowdate(), 11), add_days(nowdate(), 15), task1.name)
		task3 = create_task("_Test Task 3", add_days(nowdate(), 11), add_days(nowdate(), 15), task2.name)

		task1.update({"exp_end_date": add_days(nowdate(), 20)})
		task1.save()

		self.assertEqual(
			frappe.db.get_value("Task", task2.name, "exp_start_date"), getdate(add_days(nowdate(), 21))
		)
		self.assertEqual(
			frappe.db.get_value("Task", task2.name, "exp_end_date"), getdate(add_days(nowdate(), 25))
		)

		self.assertEqual(
			frappe.db.get_value("Task", task3.name, "exp_start_date"), getdate(add_days(nowdate(), 26))
		)
		self.assertEqual(
			frappe.db.get_value("Task", task3.name, "exp_end_date"), getdate(add_days(nowdate(), 30))
		)

	def test_child_task_does_not_reschedule_its_parent(self):
		parent = create_task("_Test Parent Not Rescheduled", nowdate(), add_days(nowdate(), 10), is_group=1)
		child = create_task(
			"_Test Child Of Parent Not Rescheduled",
			nowdate(),
			add_days(nowdate(), 3),
			parent_task=parent.name,
		)

		child.save()

		self.assertEqual(
			getdate(frappe.db.get_value("Task", parent.name, "exp_start_date")), getdate(nowdate())
		)

	def test_close_assignment(self):
		if not frappe.db.exists("Task", "Test Close Assignment"):
			task = frappe.new_doc("Task")
			task.subject = "Test Close Assignment"
			task.insert()

		def assign():
			from frappe.desk.form import assign_to

			assign_to.add(
				{
					"assign_to": ["test@example.com"],
					"doctype": task.doctype,
					"name": task.name,
					"description": "Close this task",
				}
			)

		def get_owner_and_status():
			return frappe.db.get_value(
				"ToDo",
				filters={
					"reference_type": task.doctype,
					"reference_name": task.name,
					"description": "Close this task",
				},
				fieldname=("allocated_to", "status"),
				as_dict=True,
			)

		assign()
		todo = get_owner_and_status()
		self.assertEqual(todo.allocated_to, "test@example.com")
		self.assertEqual(todo.status, "Open")

		# assignment should be
		task.load_from_db()
		task.status = "Completed"
		task.save()
		todo = get_owner_and_status()
		self.assertEqual(todo.allocated_to, "test@example.com")
		self.assertEqual(todo.status, "Closed")

	def test_overdue(self):
		task = create_task("Testing Overdue", add_days(nowdate(), -10), add_days(nowdate(), -5))

		from erpnext.projects.doctype.task.task import set_tasks_as_overdue

		set_tasks_as_overdue()

		self.assertEqual(frappe.db.get_value("Task", task.name, "status"), "Overdue")

	def test_parent_task_must_be_group(self):
		parent_task = create_task(
			subject="_Test Parent Task Non Group",
			is_group=0,
		)

		child_task = create_task(
			subject="_Test Child Task",
			parent_task=parent_task.name,
			save=False,
		)

		self.assertRaises(ParentIsGroupError, child_task.save)

	def test_actual_dates_outside_project_dates(self):
		project = frappe.get_value("Project", {"project_name": "_Test Project"})
		frappe.db.set_value(
			"Project",
			project,
			{"expected_start_date": add_days(nowdate(), -10), "expected_end_date": add_days(nowdate(), 5)},
		)
		task = create_task("_Test Task Late Work", nowdate(), add_days(nowdate(), 3))
		task.act_start_date = task.act_end_date = add_days(nowdate(), 8)

		with patch.dict(frappe.flags, {"in_test": False}):
			task.validate_parent_project_dates()

			task.exp_end_date = add_days(nowdate(), 8)
			self.assertRaises(frappe.exceptions.InvalidDates, task.validate_parent_project_dates)

	def test_template_task_is_not_overdue(self):
		task = create_task(
			"_Test Template Task Overdue", add_days(nowdate(), -10), add_days(nowdate(), -5), is_template=1
		)

		set_tasks_as_overdue()

		self.assertEqual(frappe.db.get_value("Task", task.name, "status"), "Template")

	def test_overdue_cleared_when_end_date_moves_out(self):
		task = create_task("_Test Task Overdue Moved Out", add_days(nowdate(), -10), add_days(nowdate(), -5))
		set_tasks_as_overdue()

		task.reload()
		task.exp_end_date = add_days(nowdate(), 10)
		task.save()

		self.assertEqual(task.status, "Open")

	def test_delete_child_task(self):
		parent = create_task("_Test Parent Of Deleted Child", is_group=1)
		child = create_task("_Test Deleted Child", parent_task=parent.name)

		child.delete()

		parent.reload()
		self.assertFalse(parent.depends_on)

	def test_delete_child_task_without_parent_write_permission(self):
		from frappe.core.doctype.user_permission.test_user_permission import create_user

		from erpnext.projects.doctype.project.test_project import make_project

		parent = create_task("_Test Parent In Restricted Project", is_group=1)
		child = create_task("_Test Child In Permitted Project", parent_task=parent.name)
		child_project = make_project({"project_name": "_Test Project Child Only"}).name
		frappe.db.set_value("Task", child.name, "project", child_project)
		user = create_user("test_task_child_deleter@example.com", "Projects User")
		frappe.permissions.add_user_permission("Project", child_project, user.name)

		with self.set_user(user.name):
			frappe.delete_doc("Task", child.name)

		self.assertFalse(frappe.db.exists("Task", child.name))


def create_task(
	subject,
	start=None,
	end=None,
	depends_on=None,
	project=None,
	parent_task=None,
	is_group=0,
	is_template=0,
	begin=0,
	duration=0,
	save=True,
	priority=None,
):
	if not frappe.db.exists("Task", subject):
		task = frappe.new_doc("Task")
		task.status = "Open"
		task.subject = subject
		task.exp_start_date = start or nowdate()
		task.exp_end_date = end or nowdate()
		task.project = (
			project or None if is_template else frappe.get_value("Project", {"project_name": "_Test Project"})
		)
		task.is_template = is_template
		task.start = begin
		task.duration = duration
		task.is_group = is_group
		task.parent_task = parent_task
		task.priority = priority
		if save:
			task.save()
	else:
		task = frappe.get_doc("Task", subject)

	if depends_on:
		task.append("depends_on", {"task": depends_on})
		if save:
			task.save()
	return task
