import os

import frappe
from frappe import _


def execute():
	template = frappe.db.exists("Email Template", _("Exit Questionnaire Notification"))
	if not template:
		base_path = frappe.get_app_path("erpnext", "hr", "doctype")
		response = frappe.read_file(
			os.path.join(base_path, "exit_interview/exit_questionnaire_notification_template.html")
		)

		template = frappe.get_doc(
			{
				"doctype": "Email Template",
				"name": _("Exit Questionnaire Notification"),
				"response": response,
				"subject": _("Exit Questionnaire Notification"),
				"owner": frappe.session.user,
			}
		).insert(ignore_permissions=True)
		template = template.name

	hr_settings = frappe.get_doc("HR Settings")
	hr_settings.exit_questionnaire_notification_template = template
	hr_settings.flags.ignore_links = True
	hr_settings.save()
