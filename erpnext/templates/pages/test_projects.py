# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from erpnext.projects.doctype.project.test_project import make_project
from erpnext.templates.pages.projects import validate_and_get_project_user
from erpnext.tests.utils import ERPNextTestSuite


class TestProjectsPage(ERPNextTestSuite):
	"""validate_and_get_project_user() gates the /projects portal page. It must raise
	frappe.PermissionError for a user who can't read the Project, and otherwise return
	that user's Project User row (or None if they're permitted but not listed as one --
	e.g. an internal Projects Manager browsing the portal)."""

	def _create_user(self, email):
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": "Portal",
					"send_welcome_email": 0,
				}
			).insert(ignore_permissions=True)
		return email

	def test_raises_permission_error_for_user_without_access(self):
		project = make_project({"project_name": f"_Test Portal Access {frappe.generate_hash(length=6)}"})
		outsider = self._create_user(f"outsider_{frappe.generate_hash(length=6)}@example.com")

		with self.set_user(outsider):
			self.assertRaises(frappe.PermissionError, validate_and_get_project_user, project.name)

	def test_allows_user_listed_as_project_user_and_returns_their_row(self):
		# Being a Project User shares the Project with that user (see
		# Project.control_access_for_project_users), which is what lets them past
		# check_permission() here.
		member = self._create_user(f"member_{frappe.generate_hash(length=6)}@example.com")

		project = frappe.get_doc(
			doctype="Project",
			project_name=f"_Test Portal Access {frappe.generate_hash(length=6)}",
			status="Open",
			company="_Test Company",
		)
		project.append(
			"users", {"user": member, "view_attachments": 1, "hide_timesheets": 1, "welcome_email_sent": 1}
		)
		project.insert()

		with self.set_user(member):
			project_user = validate_and_get_project_user(project.name)

		self.assertIsNotNone(project_user)
		self.assertEqual(project_user.user, member)
		self.assertEqual(project_user.view_attachments, 1)
		self.assertEqual(project_user.hide_timesheets, 1)

	def test_allows_internally_permitted_user_not_listed_as_project_user(self):
		# The permission gate must be the real permission system (check_permission()),
		# not "is this user in the Project's users child table" -- a Projects Manager
		# can open any project's portal page without ever being added as its user.
		project = make_project({"project_name": f"_Test Portal Access {frappe.generate_hash(length=6)}"})
		manager = self._create_user(f"manager_{frappe.generate_hash(length=6)}@example.com")
		frappe.get_doc("User", manager).add_roles("Projects Manager")

		with self.set_user(manager):
			project_user = validate_and_get_project_user(project.name)

		self.assertIsNone(project_user)
