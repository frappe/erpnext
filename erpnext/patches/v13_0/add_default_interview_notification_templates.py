import os

import frappe
from frappe import _


def execute():
	if not frappe.db.exists("Email Template", _("Interview Reminder")):
		base_path = frappe.get_app_path("erpnext", "hr", "doctype")
		response = frappe.read_file(
			os.path.join(base_path, "interview/interview_reminder_notification_template.html")
		)

		frappe.get_doc(
			{
				"doctype": "Email Template",
				"name": _("Interview Reminder"),
				"response": response,
				"subject": _("Interview Reminder"),
				"owner": frappe.session.user,
			}
		).insert(ignore_permissions=True)

	if not frappe.db.exists("Email Template", _("Interview Feedback Reminder")):
		base_path = frappe.get_app_path("erpnext", "hr", "doctype")
		response = frappe.read_file(
			os.path.join(base_path, "interview/interview_feedback_reminder_template.html")
		)

		frappe.get_doc(
			{
				"doctype": "Email Template",
				"name": _("Interview Feedback Reminder"),
				"response": response,
				"subject": _("Interview Feedback Reminder"),
				"owner": frappe.session.user,
			}
		).insert(ignore_permissions=True)

	hr_settings = frappe.get_doc("HR Settings")
	hr_settings.interview_reminder_template = _("Interview Reminder")
	hr_settings.feedback_reminder_notification_template = _("Interview Feedback Reminder")
	hr_settings.flags.ignore_links = True
	hr_settings.save()
