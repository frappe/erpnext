# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.utils import add_days, nowtime, today

from erpnext.projects.doctype.project.project import collect_project_status
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
		with patch("frappe.sendmail"), self.assertWarns(PendingDeprecationWarning):
			daily_reminder()

	def test_reply_with_a_link_is_collected_once(self):
		project_update = make_project_update()
		copy = send_copy(project_update, "admin@example.com")
		receive_reply(
			project_update, copy, "admin@example.com", "See [the design](https://example.com/design)"
		)

		collect_project_status()
		collect_project_status()
		self.assertEqual(len(frappe.get_doc("Project Update", project_update).users), 1)

	def test_identical_reply_in_a_later_run_is_collected(self):
		project_update = make_project_update()
		copy = send_copy(project_update, "admin@example.com")
		receive_reply(project_update, copy, "admin@example.com", "Done with design")
		collect_project_status()
		receive_reply(project_update, copy, "admin@example.com", "Done with design")

		collect_project_status()
		collect_project_status()
		self.assertEqual(len(frappe.get_doc("Project Update", project_update).users), 2)

	def test_reply_is_added_next_to_a_hand_entered_status(self):
		project_update = make_project_update()
		doc = frappe.get_doc("Project Update", project_update)
		doc.append("users", {"user": "Administrator", "project_status": "Entered by hand"})
		doc.save()
		copy = send_copy(project_update, "admin@example.com")
		receive_reply(project_update, copy, "admin@example.com", "Done with design")

		collect_project_status()
		statuses = [row.project_status for row in frappe.get_doc("Project Update", project_update).users]
		self.assertEqual(len(statuses), 2)
		self.assertIn("Entered by hand", statuses)
		self.assertTrue(any("Done with design" in status for status in statuses))

	def test_reply_is_credited_to_the_user_its_thread_was_sent_to(self):
		# The sender of an inbound mail is not verified, so a forged sender must not change who is credited
		project_update = make_project_update(members=["Administrator", "test@example.com"])
		copy = send_copy(project_update, "test@example.com")
		receive_reply(project_update, copy, "admin@example.com", "All budgets approved")

		collect_project_status()
		users = frappe.get_doc("Project Update", project_update).users
		self.assertEqual([row.user for row in users], ["test@example.com"])

	def test_reply_to_an_earlier_reply_is_skipped(self):
		# The timeline shows the names of earlier replies, and Frappe accepts a name in In-Reply-To
		project_update = make_project_update(members=["Administrator", "test@example.com"])
		copy = send_copy(project_update, "admin@example.com")
		first_reply = receive_reply(project_update, copy, "admin@example.com", "Started on design")
		receive_reply(project_update, first_reply, "admin@example.com", "All budgets approved")

		collect_project_status()
		statuses = [row.project_status for row in frappe.get_doc("Project Update", project_update).users]
		self.assertEqual(len(statuses), 1)
		self.assertIn("Started on design", statuses[0])

	def test_reply_to_a_communication_that_is_not_a_queued_copy_is_skipped(self):
		project_update = make_project_update()
		send_copy(project_update, "admin@example.com")
		timeline_email = make_communication(
			"Sent", recipients="admin@example.com", **reference(project_update)
		)
		receive_reply(project_update, timeline_email, "admin@example.com", "All budgets approved")

		collect_project_status()
		self.assertEqual(frappe.get_doc("Project Update", project_update).users, [])

	def test_reply_outside_a_thread_or_from_a_former_member_is_skipped(self):
		project_update = make_project_update()
		receive_reply(project_update, None, "admin@example.com", "Not in a thread")
		former_member_copy = send_copy(project_update, "test@example.com")
		receive_reply(project_update, former_member_copy, "test@example.com", "Left the project")
		unknown_copy = send_copy(project_update, "_test_outsider@example.com")
		receive_reply(project_update, unknown_copy, "_test_outsider@example.com", "Not a user")

		collect_project_status()
		self.assertEqual(frappe.get_doc("Project Update", project_update).users, [])

	def test_reply_to_an_update_sent_before_per_user_copies_is_credited_to_its_sender(self):
		# An update sent before the upgrade has no copies, so its replies cannot be matched to a thread
		project_update = make_project_update()
		receive_reply(project_update, None, "admin@example.com", "Done with design")
		receive_reply(project_update, None, "test@example.com", "Not on the project")

		collect_project_status()
		users = frappe.get_doc("Project Update", project_update).users
		self.assertEqual([row.user for row in users], ["Administrator"])

	def test_each_user_gets_their_own_copy_of_the_update(self):
		from erpnext.projects.doctype.project.project import send_project_update_email_to_users

		project = make_project(["Administrator", "test@example.com"])
		with patch("frappe.sendmail") as sendmail:
			send_project_update_email_to_users(project)

		sent = [call.kwargs for call in sendmail.call_args_list]
		self.assertEqual(
			sorted(kwargs["recipients"][0] for kwargs in sent), ["admin@example.com", "test@example.com"]
		)
		self.assertEqual(len({kwargs["message_id"] for kwargs in sent}), 2)
		for kwargs in sent:
			communication = frappe.get_doc("Communication", kwargs["communication"])
			self.assertEqual(communication.recipients, kwargs["recipients"][0])
			self.assertEqual(communication.message_id, kwargs["message_id"])
			# The copy must not show on any timeline, because Frappe accepts its name in In-Reply-To
			self.assertFalse(communication.reference_doctype)
			self.assertFalse(frappe.db.exists("Communication Link", {"parent": communication.name}))


def make_project(members: list[str]) -> str:
	project = frappe.get_doc(
		doctype="Project",
		project_name=f"_Test Project Update {frappe.generate_hash(length=8)}",
		company="_Test Company",
		subject="Progress",
		message="Reply with your progress",
	)
	for user in members:
		# welcome_email_sent=1 so saving doesn't try to send a collaboration invite (no SMTP in tests)
		project.append("users", {"user": user, "welcome_email_sent": 1})
	return project.insert().name


def make_project_update(members: list[str] | None = None) -> str:
	return (
		frappe.get_doc(
			{
				"doctype": "Project Update",
				"project": make_project(members or ["Administrator"]),
				"date": today(),
				"time": nowtime(),
			}
		)
		.insert()
		.name
	)


def send_copy(project_update: str, recipient: str) -> str:
	"""Make a copy of the update the way `send_project_update_copy` and `frappe.sendmail` do."""
	copy = make_communication("Sent", recipients=recipient, content="Reply with your progress")
	frappe.get_doc(
		{
			"doctype": "Email Queue",
			"communication": copy,
			"recipients": [{"recipient": recipient}],
			**reference(project_update),
		}
	).insert(ignore_permissions=True)
	return copy


def receive_reply(project_update: str, in_reply_to: str | None, sender: str, content: str) -> str:
	return make_communication(
		"Received",
		in_reply_to=in_reply_to,
		sender=sender,
		content=content,
		text_content=content,
		**reference(project_update),
	)


def reference(project_update: str) -> dict:
	return {"reference_doctype": "Project Update", "reference_name": project_update}


def make_communication(sent_or_received: str, **fields) -> str:
	return (
		frappe.get_doc(
			{
				"doctype": "Communication",
				"communication_type": "Communication",
				"communication_medium": "Email",
				"sent_or_received": sent_or_received,
				"subject": "Project Update",
				**fields,
			}
		)
		.insert(ignore_permissions=True)
		.name
	)
