# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.utils import add_days, today

from erpnext.tests.utils import ERPNextTestSuite


class TestProjectUpdate(ERPNextTestSuite):
	def test_daily_reminder_runs_and_finds_yesterdays_update(self):
		# daily_reminder previously selected non-existent Project Update columns (progress /
		# progress_details), raising on both engines. Verify the converted query finds yesterday's
		# update and that the whole reminder flow runs without error.
		from erpnext.projects.doctype.project.test_project import make_project
		from erpnext.projects.doctype.project_update.project_update import daily_reminder

		project = make_project({"project_name": "_Test Project Update Reminder", "company": "_Test Company"})
		project.db_set("frequency", "Daily")

		# Project autonames by naming series, so project.name (PROJ-xxxx) differs from project_name.
		# The reminder must filter on project.name, not the display name.
		self.assertNotEqual(project.name, project.project_name)

		user = "_test_project_reminder@example.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc(
				{"doctype": "User", "email": user, "first_name": "PR", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		if user not in [u.user for u in project.users]:
			# welcome_email_sent=1 so saving doesn't try to send a collaboration invite (no SMTP in tests)
			project.append("users", {"user": user, "welcome_email_sent": 1})
			project.save()

		pu = frappe.get_doc(
			{
				"doctype": "Project Update",
				"project": project.name,
				"date": add_days(today(), -1),
				"time": "10:00:00",
			}
		).insert()
		self.addCleanup(frappe.delete_doc, "Project Update", pu.name, force=1)

		# The converted update query (no longer referencing progress/progress_details) must find
		# yesterday's Project Update, keyed on project.name, on both engines.
		updates = frappe.get_all(
			"Project Update",
			filters={"project": project.name, "date": add_days(today(), -1)},
			fields=["name", "date", "time"],
			as_list=True,
		)
		self.assertIn(pu.name, [u[0] for u in updates])

		# Project Users are stored under project.name, not project_name: the reminder must use the
		# document key to resolve recipients (the display name matches nothing).
		self.assertIn(user, frappe.get_all("Project User", filters={"parent": project.name}, pluck="user"))
		self.assertEqual(
			frappe.get_all("Project User", filters={"parent": project.project_name}, pluck="user"), []
		)

		# The full reminder flow runs without error (Project / Project Update / Holiday / Project
		# User lookups all execute). sendmail is mocked so no SMTP account is required.
		with patch("frappe.sendmail"):
			daily_reminder()
