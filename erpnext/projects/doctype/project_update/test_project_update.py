# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowtime, today

from erpnext.projects.doctype.project.project import collect_project_status


class TestProjectUpdate(FrappeTestCase):
	def test_replies_are_collected_once(self):
		project_update = make_project_update()
		receive_reply(project_update, "admin@example.com", "Done with design")

		collect_project_status()
		collect_project_status()
		self.assertEqual(len(frappe.get_doc("Project Update", project_update).users), 1)

	def test_identical_reply_in_a_later_run_is_collected(self):
		project_update = make_project_update()
		receive_reply(project_update, "admin@example.com", "Done with design")
		collect_project_status()
		receive_reply(project_update, "admin@example.com", "Done with design")

		collect_project_status()
		collect_project_status()
		self.assertEqual(len(frappe.get_doc("Project Update", project_update).users), 2)

	def test_reply_is_added_next_to_a_hand_entered_status(self):
		project_update = make_project_update()
		doc = frappe.get_doc("Project Update", project_update)
		doc.append("users", {"user": "Administrator", "project_status": "Entered by hand"})
		doc.save()
		receive_reply(project_update, "admin@example.com", "Done with design")

		collect_project_status()
		statuses = [row.project_status for row in frappe.get_doc("Project Update", project_update).users]
		self.assertEqual(len(statuses), 2)
		self.assertIn("Entered by hand", statuses)
		self.assertTrue(any("Done with design" in status for status in statuses))


test_records = frappe.get_test_records("Project Update")
test_ignore = ["Sales Order"]


def make_project_update():
	return (
		frappe.get_doc(
			{
				"doctype": "Project Update",
				"project": frappe.get_value("Project", {"project_name": "_Test Project"}),
				"date": today(),
				"time": nowtime(),
			}
		)
		.insert()
		.name
	)


def receive_reply(project_update, sender, content):
	frappe.get_doc(
		{
			"doctype": "Communication",
			"communication_type": "Communication",
			"sent_or_received": "Received",
			"sender": sender,
			"subject": "Re: Project Update",
			"content": content,
			"text_content": content,
			"reference_doctype": "Project Update",
			"reference_name": project_update,
		}
	).insert(ignore_permissions=True)
