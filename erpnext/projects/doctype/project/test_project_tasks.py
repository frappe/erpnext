# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import json
from unittest.mock import patch

import frappe
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.permissions import add_permission

from erpnext.projects.doctype.project import project_tasks
from erpnext.projects.doctype.project.project_tasks import get_project_task_list
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
