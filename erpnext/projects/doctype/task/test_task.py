# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from unittest.mock import patch

import frappe
from frappe.utils import add_days, getdate, nowdate

from erpnext.projects.doctype.task.task import (
	CircularReferenceError,
	ParentIsGroupError,
	set_tasks_as_overdue,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestTask(ERPNextTestSuite):
	def test_task_total_costing_and_billing_amount(self):
		from erpnext.projects.doctype.project.test_project import make_project
		from erpnext.projects.doctype.timesheet.test_timesheet import make_timesheet
		from erpnext.setup.doctype.employee.test_employee import make_employee

		project_name = "Test Project Costing"
		employee = make_employee("employee@frappe.io", company="_Test Company")
		project = make_project({"project_name": project_name})
		task = create_task("_Test Task 1")
		task.project = project.name
		task.save()
		timesheet = make_timesheet(
			employee=employee,
			is_billable=1,
			currency="USD",
			project=project.name,
			simulate=True,
			exchange_rate=80,
			task=task.name,
		)
		timesheet.reload()
		project.reload()
		task.reload()
		self.assertEqual(task.total_costing_amount, 3200)
		self.assertEqual(task.total_billing_amount, 8000)

	def test_move_task_to_another_project(self):
		from erpnext.projects.doctype.project.test_project import make_project

		old_project = make_project({"project_name": "_Test Project Task Moved Out"})
		new_project = make_project({"project_name": "_Test Project Task Moved In"})
		completed_task = create_task("_Test Task Completed In Old Project", save=False)
		completed_task.update({"project": old_project.name, "status": "Completed"})
		completed_task.save()
		moved_task = create_task("_Test Task Moved", save=False)
		moved_task.project = old_project.name
		moved_task.save()

		moved_task.project = new_project.name
		moved_task.save()

		self.assertEqual(frappe.db.get_value("Project", old_project.name, "percent_complete"), 100)

	def test_timesheet_on_cancelled_task(self):
		from erpnext.projects.doctype.timesheet.test_timesheet import make_timesheet
		from erpnext.setup.doctype.employee.test_employee import make_employee

		task = create_task("_Test Cancelled Task With Timesheet")
		task.status = "Cancelled"
		task.save()
		employee = make_employee("test_task_cancelled_timesheet@example.com", company="_Test Company")

		self.assertRaises(
			frappe.ValidationError,
			make_timesheet,
			employee,
			simulate=True,
			project=task.project,
			task=task.name,
		)

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
			getdate(frappe.db.get_value("Task", task2.name, "exp_start_date")),
			getdate(add_days(nowdate(), 21)),
		)

		self.assertEqual(
			getdate(frappe.db.get_value("Task", task2.name, "exp_end_date")), getdate(add_days(nowdate(), 25))
		)

		self.assertEqual(
			getdate(frappe.db.get_value("Task", task3.name, "exp_start_date")),
			getdate(add_days(nowdate(), 26)),
		)

		self.assertEqual(
			getdate(frappe.db.get_value("Task", task3.name, "exp_end_date")), getdate(add_days(nowdate(), 30))
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

	def test_reschedule_started_dependent_tasks(self):
		prerequisite = create_task("_Test Task Before Started Tasks", nowdate(), add_days(nowdate(), 2))
		working = create_task(
			"_Test Working Dependent", add_days(nowdate(), 1), add_days(nowdate(), 3), prerequisite.name
		)
		overdue = create_task(
			"_Test Overdue Dependent", add_days(nowdate(), -3), add_days(nowdate(), -1), prerequisite.name
		)
		working.db_set("status", "Working")
		overdue.db_set("status", "Overdue")

		prerequisite.save()

		for task in (working, overdue):
			self.assertEqual(
				getdate(frappe.db.get_value("Task", task.name, "exp_start_date")),
				getdate(add_days(nowdate(), 3)),
			)

	def test_reschedule_past_parent_end_date_warns(self):
		parent = create_task("_Test Group Ending Soon", nowdate(), add_days(nowdate(), 10), is_group=1)
		prerequisite = create_task("_Test Task Before Grouped Task", nowdate(), add_days(nowdate(), 2))
		dependent = create_task(
			"_Test Grouped Dependent",
			add_days(nowdate(), 3),
			add_days(nowdate(), 5),
			prerequisite.name,
			parent_task=parent.name,
		)

		prerequisite.exp_end_date = add_days(nowdate(), 8)
		prerequisite.save()

		self.assertEqual(
			getdate(frappe.db.get_value("Task", dependent.name, "exp_end_date")),
			getdate(add_days(nowdate(), 11)),
		)
		self.assertIn(dependent.name, frappe.get_message_log()[-1]["message"])

	def test_reschedule_dependent_task_from_actual_end_date(self):
		prerequisite = create_task("_Test Task Actual End", save=False)
		prerequisite.exp_start_date = prerequisite.exp_end_date = None
		prerequisite.save()
		dependent = create_task(
			"_Test Task After Actual End", add_days(nowdate(), -5), add_days(nowdate(), -3), prerequisite.name
		)

		prerequisite.act_end_date = nowdate()
		prerequisite.save()

		self.assertEqual(
			getdate(frappe.db.get_value("Task", dependent.name, "exp_start_date")),
			getdate(add_days(nowdate(), 1)),
		)

	def test_actual_dates_outside_project_dates(self):
		project = frappe.get_value("Project", {"project_name": "_Test Project"})
		frappe.db.set_value(
			"Project",
			project,
			{"expected_start_date": add_days(nowdate(), -10), "expected_end_date": add_days(nowdate(), 5)},
		)
		task = create_task("_Test Task Late Work", nowdate(), add_days(nowdate(), 3))
		task.act_start_date = task.act_end_date = add_days(nowdate(), 8)

		with patch.object(frappe, "in_test", False):
			task.validate_parent_project_dates()

			task.exp_end_date = add_days(nowdate(), 8)
			self.assertRaises(frappe.exceptions.InvalidDates, task.validate_parent_project_dates)

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

	def test_complete_assigned_task_without_task_read_permission(self):
		from frappe.core.doctype.user_permission.test_user_permission import create_user
		from frappe.desk.form import assign_to

		task = create_task("_Test Assigned Task Completed By Timesheet")
		assign_to.add({"doctype": task.doctype, "name": task.name, "assign_to": ["test@example.com"]})
		user = create_user("test_task_timesheet_user@example.com", "HR User")

		with self.set_user(user.name):
			task.status = "Completed"
			task.save(ignore_permissions=True)

		self.assertEqual(
			frappe.db.get_value(
				"ToDo", {"reference_type": task.doctype, "reference_name": task.name}, "status"
			),
			"Closed",
		)

	def test_overdue(self):
		task = create_task("Testing Overdue", add_days(nowdate(), -10), add_days(nowdate(), -5))

		set_tasks_as_overdue()

		self.assertEqual(frappe.db.get_value("Task", task.name, "status"), "Overdue")

	def test_overdue_cleared_when_end_date_moves_out(self):
		task = create_task("_Test Task Overdue Moved Out", add_days(nowdate(), -10), add_days(nowdate(), -5))
		set_tasks_as_overdue()

		task.reload()
		task.exp_end_date = add_days(nowdate(), 10)
		task.save()

		self.assertEqual(task.status, "Open")

	def test_task_due_today_is_not_overdue(self):
		task = create_task("_Test Task Due Today", add_days(nowdate(), -2), nowdate())

		set_tasks_as_overdue()

		self.assertEqual(frappe.db.get_value("Task", task.name, "status"), "Open")

	def test_template_task_is_not_overdue(self):
		task = create_task(
			"_Test Template Task Overdue", add_days(nowdate(), -10), add_days(nowdate(), -5), is_template=1
		)

		set_tasks_as_overdue()

		self.assertEqual(frappe.db.get_value("Task", task.name, "status"), "Template")

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

	def test_parent_task_must_be_in_the_same_project(self):
		other_project = frappe.get_doc(
			doctype="Project", project_name="_Test Parent Task Project", company="_Test Company"
		).insert()
		group = frappe.get_doc(
			doctype="Task", subject="_Test Other Project Group", project=other_project.name, is_group=1
		).insert()

		child_task = create_task("_Test Child In Another Project", parent_task=group.name, save=False)
		self.assertRaises(frappe.ValidationError, child_task.save)

		child_without_project = frappe.get_doc(
			doctype="Task", subject="_Test Child Without Project", parent_task=group.name
		).insert()
		self.assertEqual(child_without_project.project, other_project.name)

	def test_open_task_under_completed_parent(self):
		parent = create_task("_Test Completed Parent", is_group=1)
		parent.status = "Completed"
		parent.save()
		child = create_task("_Test Open Child Of Completed Parent", parent_task=parent.name, save=False)

		self.assertRaises(frappe.ValidationError, child.save)

	def test_expected_end_date(self):
		task = create_task("Testing End Date", add_days(nowdate(), 1), add_days(nowdate(), 5))
		task.expected_time = 72
		task.save()
		self.assertEqual(getdate(task.exp_end_date), getdate(add_days(nowdate(), 5)))

	def test_set_multiple_status(self):
		from erpnext.projects.doctype.task.task import set_multiple_status

		task1 = create_task("_Test Bulk Status 1")
		task2 = create_task("_Test Bulk Status 2")

		set_multiple_status(frappe.as_json([task1.name, task2.name]), "Completed")

		self.assertEqual(frappe.db.get_value("Task", task1.name, "status"), "Completed")
		self.assertEqual(frappe.db.get_value("Task", task2.name, "status"), "Completed")

	def test_completing_sets_completed_on(self):
		from frappe.core.doctype.user_permission.test_user_permission import create_user

		task = create_task("_Test Complete Without Date")
		user = create_user("test_task_completer@example.com", "Projects User")
		with self.set_user(user.name):
			frappe.set_value("Task", task.name, "status", "Completed")

		self.assertEqual(frappe.db.get_value("Task", task.name, "completed_on"), getdate())

	def test_negative_progress(self):
		task = create_task("_Test Task Negative Progress", save=False)
		task.progress = -50

		self.assertRaises(frappe.ValidationError, task.save)

	def test_reopen_completed_task(self):
		task = create_task("_Test Task Reopened")
		task.status = "Completed"
		task.save()

		task.status = "Open"
		task.save()
		self.assertEqual((task.progress, task.completed_on), (0, None))

		task.status = "Completed"
		task.save()
		task.update({"status": "Working", "progress": 60})
		task.save()
		self.assertEqual(task.progress, 60)

	def test_add_multiple_tasks_under_parent(self):
		from erpnext.projects.doctype.task.task import add_multiple_tasks

		parent = create_task("_Test Bulk Parent", is_group=1)
		rows = [{"subject": "_Test Bulk Child A"}, {"subject": ""}, {"subject": "_Test Bulk Child B"}]

		add_multiple_tasks(frappe.as_json(rows), parent.name)

		children = frappe.get_all("Task", filters={"parent_task": parent.name}, pluck="subject")
		# the row with a blank subject is skipped
		self.assertEqual(sorted(children), ["_Test Bulk Child A", "_Test Bulk Child B"])

	def test_add_multiple_tasks_under_project_root(self):
		from erpnext.projects.doctype.task.task import add_multiple_tasks

		project = frappe.get_value("Project", {"project_name": "_Test Project"})

		add_multiple_tasks(frappe.as_json([{"subject": "_Test Bulk Root Task"}]), project, project)

		self.assertEqual(
			frappe.db.get_value("Task", {"subject": "_Test Bulk Root Task"}, ["project", "parent_task"]),
			(project, None),
		)

	def test_template_task_dependency_must_be_template(self):
		normal_task = create_task("_Test Non Template Dependency")
		template_task = create_task("_Test Template With Dependency", is_template=1, save=False)
		template_task.append("depends_on", {"task": normal_task.name})

		self.assertRaises(frappe.ValidationError, template_task.save)

	def test_cannot_delete_task_with_children(self):
		parent = create_task("_Test Parent With Child", is_group=1)
		create_task("_Test Child Blocking Delete", parent_task=parent.name)

		self.assertRaises(frappe.ValidationError, parent.delete)

	def test_delete_child_task(self):
		parent = create_task("_Test Parent Of Deleted Child", is_group=1)
		child = create_task("_Test Deleted Child", parent_task=parent.name)

		child.delete()

		parent.reload()
		self.assertFalse(parent.depends_on)

	def test_move_child_task_to_another_parent(self):
		old_parent = create_task("_Test Old Parent", is_group=1)
		new_parent = create_task("_Test New Parent", is_group=1)
		child = create_task("_Test Moved Child", parent_task=old_parent.name)

		child.parent_task = new_parent.name
		child.save()

		self.assertFalse(frappe.get_all("Task Depends On", filters={"parent": old_parent.name}))
		self.assertEqual(
			frappe.get_all("Task Depends On", filters={"parent": new_parent.name}, pluck="task"), [child.name]
		)

	def test_child_task_registers_in_parent_depends_on(self):
		parent = create_task("_Test Parent Depends On", is_group=1)
		child = create_task("_Test Child Depends On", parent_task=parent.name)

		parent.reload()
		self.assertIn(child.name, [row.task for row in parent.depends_on])

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

	def test_child_tasks_are_listed_only_for_a_readable_task(self):
		from frappe.core.doctype.user_permission.test_user_permission import create_user

		from erpnext.projects.doctype.project.test_project import make_project
		from erpnext.projects.doctype.task.task import check_if_child_exists

		group = create_task("_Test Group Hidden From User", is_group=1)
		create_task("_Test Child Hidden From User", parent_task=group.name)
		user = create_user("test_task_child_lister@example.com", "Projects User")
		other_project = make_project({"project_name": "_Test Project Child Lister"}).name
		frappe.permissions.add_user_permission("Project", other_project, user.name)

		with self.set_user(user.name):
			self.assertRaises(frappe.PermissionError, check_if_child_exists, group.name)


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
