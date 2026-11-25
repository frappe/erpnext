# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import json
from unittest.mock import patch

import frappe
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.permissions import add_permission, add_user_permission, setup_custom_perms

from erpnext.projects.doctype.project import project_tasks
from erpnext.projects.doctype.project.project_tasks import create_task, get_project_task_list
from erpnext.projects.doctype.project.test_project import make_project
from erpnext.tests.utils import ERPNextTestSuite

SHARED_USER = "tasks-board-shared@example.com"
PROJECTS_USER = "tasks-board-projects-user@example.com"


class TestProjectTasks(ERPNextTestSuite):
	def setUp(self):
		self.project = make_project({"project_name": "_Test Tasks Board"}).name
		self.phase = self.make_task("Phase", is_group=1)
		self.stage = self.make_task("Stage", is_group=1, parent_task=self.phase)
		self.deep = self.make_task("Deep", parent_task=self.stage)
		self.child = self.make_task("Child", parent_task=self.phase)
		self.loose = self.make_task("Loose")
		self.other_phase = self.make_task("Other phase", is_group=1)
		self.other_child = self.make_task("Other child", parent_task=self.other_phase)

	def make_task(self, subject, project=None, **values):
		return (
			frappe.get_doc(doctype="Task", subject=subject, project=project or self.project, **values)
			.insert()
			.name
		)

	def board(self, user="Administrator"):
		with self.set_user(user):
			data = get_project_task_list(self.project)
		return data, {row.name: row for row in data["tasks"]}

	def test_returns_the_project_tasks_with_their_top_parent(self):
		self.make_task("In another project", project=make_project({"project_name": "_Test Tasks Other"}).name)
		frappe.db.set_value("Task", self.child, "_assign", json.dumps(["test@example.com"]))

		data, rows = self.board()

		self.assertEqual(
			set(rows),
			{
				self.phase,
				self.stage,
				self.deep,
				self.child,
				self.loose,
				self.other_phase,
				self.other_child,
			},
		)
		self.assertEqual(rows[self.deep].top_parent, self.phase)
		self.assertEqual(rows[self.child].top_parent, self.phase)
		self.assertEqual(rows[self.other_child].top_parent, self.other_phase)
		self.assertIsNone(rows[self.loose].top_parent)
		self.assertIsNone(rows[self.phase].top_parent)

		self.assertEqual(rows[self.child].assigned_to, ["test@example.com"])
		self.assertEqual(rows[self.loose].assigned_to, [])
		self.assertNotIn("_assign", rows[self.child])
		self.assertNotIn("lft", rows[self.child])
		self.assertIn("assigned_to", data["fields"])
		self.assertNotIn("_assign", data["fields"])

		self.assertEqual(data["options"]["priority"], ["Low", "Medium", "High", "Urgent"])
		self.assertEqual(data["editable"], ["status", "priority"])
		self.assertTrue(data["can_create"])
		self.assertFalse(data["truncated"])
		self.assertTrue(all(row.can_write for row in rows.values()))

	def test_shows_only_shared_tasks_and_no_hidden_parent(self):
		create_user(SHARED_USER, "Desk User")
		frappe.share.add_docshare("Project", self.project, user=SHARED_USER, read=1)
		frappe.share.add_docshare("Task", self.deep, user=SHARED_USER, read=1)
		frappe.share.add_docshare("Task", self.loose, user=SHARED_USER, read=1, write=1)
		frappe.share.add_docshare("Task", self.other_phase, user=SHARED_USER, read=1)
		frappe.share.add_docshare("Task", self.other_child, user=SHARED_USER, read=1)

		data, rows = self.board(SHARED_USER)

		self.assertEqual(set(rows), {self.deep, self.loose, self.other_phase, self.other_child})
		# Deep's top-level parent isn't shared, so the tab must not name it
		self.assertIsNone(rows[self.deep].top_parent)
		self.assertEqual(rows[self.other_child].top_parent, self.other_phase)

		self.assertTrue(rows[self.loose].can_write)
		self.assertFalse(rows[self.deep].can_write)
		# shared for writing, so permlevel 0 fields save; the row's can_write decides the rest
		self.assertEqual(data["editable"], ["status", "priority"])
		self.assertFalse(data["can_create"])

	def per_task_checks(self, user):
		"""The tab's rows for `user`, and how many write checks loaded a task of their own."""
		with patch("frappe.has_permission", wraps=frappe.has_permission) as check:
			data, rows = self.board(user)
		per_task = [
			call for call in check.call_args_list if call.args[:1] == ("Task",) and call.kwargs.get("doc")
		]
		return rows, len(per_task)

	def test_decides_write_access_once_from_roles_and_shares(self):
		create_user(SHARED_USER, "Desk User")
		frappe.share.add_docshare("Project", self.project, user=SHARED_USER, read=1)
		frappe.share.add_docshare("Task", self.deep, user=SHARED_USER, read=1)
		frappe.share.add_docshare("Task", self.loose, user=SHARED_USER, read=1, write=1)

		rows, per_task = self.per_task_checks(SHARED_USER)

		self.assertEqual(per_task, 0)
		self.assertTrue(rows[self.loose].can_write)
		self.assertFalse(rows[self.deep].can_write)

	def make_own_tasks_only_writable(self):
		"""Projects Users read every task but write only the ones they made; returns one they made."""
		create_user(PROJECTS_USER, "Projects User")
		self.addCleanup(frappe.clear_cache, doctype="Task")
		setup_custom_perms("Task")
		frappe.db.set_value(
			"Custom DocPerm",
			{"parent": "Task", "role": "Projects User", "permlevel": 0, "if_owner": 0},
			"write",
			0,
		)
		frappe.get_doc(
			doctype="Custom DocPerm",
			parent="Task",
			parenttype="DocType",
			parentfield="permissions",
			role="Projects User",
			permlevel=0,
			if_owner=1,
			read=1,
			write=1,
		).insert()
		frappe.clear_cache(doctype="Task")
		with self.set_user(PROJECTS_USER):
			return self.make_task("Made by the user")

	def test_writes_only_own_tasks_where_the_role_says_so(self):
		own = self.make_own_tasks_only_writable()

		rows, per_task = self.per_task_checks(PROJECTS_USER)

		self.assertEqual(per_task, 0)
		self.assertTrue(rows[own].can_write)
		self.assertFalse(rows[self.loose].can_write)

	def test_writes_own_tasks_when_a_user_permission_applies_too(self):
		own = self.make_own_tasks_only_writable()
		add_user_permission("Project", self.project, PROJECTS_USER)

		rows, per_task = self.per_task_checks(PROJECTS_USER)

		self.assertEqual(per_task, len(rows))
		self.assertTrue(rows[own].can_write)
		self.assertFalse(rows[self.loose].can_write)

	def test_checks_no_task_for_a_user_who_can_write_none(self):
		create_user(SHARED_USER, "Desk User")
		frappe.share.add_docshare("Project", self.project, user=SHARED_USER, read=1)
		frappe.share.add_docshare("Task", self.loose, user=SHARED_USER, read=1)
		add_user_permission("Project", self.project, SHARED_USER)

		rows, per_task = self.per_task_checks(SHARED_USER)

		self.assertEqual(per_task, 0)
		self.assertFalse(rows[self.loose].can_write)

	def test_checks_each_task_where_a_user_permission_applies(self):
		create_user(PROJECTS_USER, "Projects User")
		add_user_permission("Project", self.project, PROJECTS_USER)

		rows, per_task = self.per_task_checks(PROJECTS_USER)

		self.assertEqual(per_task, len(rows))
		self.assertTrue(all(row.can_write for row in rows.values()))

	def test_refuses_a_project_the_user_cannot_read(self):
		create_user(SHARED_USER, "Desk User")
		with self.set_user(SHARED_USER):
			self.assertRaises(frappe.PermissionError, get_project_task_list, self.project)

	def test_leaves_out_fields_the_user_cannot_read_or_write(self):
		create_user(PROJECTS_USER, "Projects User")
		# after the rollback, so the cached meta matches the database again
		self.addCleanup(frappe.clear_cache, doctype="Task")
		make_property_setter("Task", "priority", "permlevel", 1, "Int")
		frappe.clear_cache(doctype="Task")

		data, rows = self.board(PROJECTS_USER)
		self.assertNotIn("priority", data["fields"])
		self.assertNotIn("priority", data["options"])
		self.assertNotIn("priority", rows[self.loose])
		self.assertEqual(data["editable"], ["status"])

		# readable at permlevel 1 now, but still not writable
		add_permission("Task", "Projects User", permlevel=1)
		frappe.clear_cache(doctype="Task")

		data, rows = self.board(PROJECTS_USER)
		self.assertIn("priority", data["fields"])
		self.assertIn("priority", rows[self.loose])
		self.assertEqual(data["editable"], ["status"])

	def test_stops_at_the_task_limit(self):
		with patch.object(project_tasks, "TASK_LIMIT", 2):
			data, rows = self.board()

		self.assertTrue(data["truncated"])
		self.assertEqual(len(rows), 2)

	def test_creates_a_task_and_assigns_it(self):
		task = create_task(
			# an owner in the values is not the dialog's to set
			{
				"subject": "Made in the dialog",
				"project": self.project,
				"status": "Working",
				"priority": "High",
				"parent_task": self.phase,
				"owner": "someone@example.com",
			},
			["test@example.com"],
		)

		self.assertEqual(
			(task.project, task.status, task.priority, task.parent_task),
			(self.project, "Working", "High", self.phase),
		)
		self.assertEqual(task.owner, "Administrator")
		# `_assign` isn't in what's returned, which only needs the task to hand to its caller
		self.assertEqual(
			frappe.parse_json(frappe.db.get_value("Task", task.name, "_assign")), ["test@example.com"]
		)

	def test_returns_only_the_fields_the_user_can_read(self):
		create_user(PROJECTS_USER, "Projects User")
		self.addCleanup(frappe.clear_cache, doctype="Task")
		make_property_setter("Task", "priority", "permlevel", 1, "Int")
		frappe.clear_cache(doctype="Task")

		with self.set_user(PROJECTS_USER):
			task = create_task({"subject": "Made by a Projects User", "project": self.project})

		self.assertEqual(task.subject, "Made by a Projects User")
		# saved with its default, but not the user's to read
		self.assertTrue(frappe.db.get_value("Task", task.name, "priority"))
		self.assertIsNone(task.priority)

	def test_creates_a_task_without_a_project(self):
		task = create_task({"subject": "No project"})
		self.assertFalse(task.project)
		self.assertTrue(frappe.db.exists("Task", task.name))

	def test_refuses_an_assignee_the_assign_dialog_refuses(self):
		website_user = "tasks-board-website-user@example.com"
		if not frappe.db.exists("User", website_user):
			frappe.get_doc(
				doctype="User",
				email=website_user,
				first_name="Website",
				user_type="Website User",
				send_welcome_email=0,
			).insert()

		self.assertRaises(
			frappe.ValidationError, create_task, {"subject": "Assigned outside desk"}, [website_user]
		)
		self.assertFalse(frappe.db.exists("ToDo", {"allocated_to": website_user}))

	def test_keeps_what_the_opening_page_filled_in(self):
		# the "+" on an Issue's dashboard starts the task with its Issue, which the dialog doesn't show
		issue = frappe.get_doc(doctype="Issue", subject="Task from an issue").insert().name
		task = create_task(
			# the task tree and the fields every document has stay the system's to set
			{"subject": "From an issue", "issue": issue, "lft": 999999, "name": "TASK-FROM-ISSUE"}
		)

		self.assertEqual(task.issue, issue)
		self.assertNotEqual(task.name, "TASK-FROM-ISSUE")
		self.assertNotEqual(task.lft, 999999)

	def test_refuses_a_user_who_cannot_create_tasks(self):
		create_user(SHARED_USER, "Desk User")
		frappe.share.add_docshare("Project", self.project, user=SHARED_USER, read=1)

		with self.set_user(SHARED_USER):
			self.assertRaises(
				frappe.PermissionError, create_task, {"subject": "Not allowed", "project": self.project}
			)
		self.assertFalse(frappe.db.exists("Task", {"subject": "Not allowed"}))
