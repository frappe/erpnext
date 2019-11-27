from __future__ import unicode_literals
import os

import frappe
from frappe import _


def execute():
	frappe.reload_doc("email", "doctype", "email_template")
	frappe.reload_doc("hr", "doctype", "hr_settings")

	if not frappe.db.exists("Email Template", _("Birthday Email Notification")):
		base_path = frappe.get_app_path("erpnext", "templates", "emails")
		response = frappe.read_file(os.path.join(base_path, "birthday_email_notification.html"))

		frappe.get_doc({
			"doctype": "Email Template",
			"name": _("Birthday Email Notification"),
			"response": response,
			"subject": _("Happy Birthday!"),
			"owner": frappe.session.user,
		}).insert(ignore_permissions=True)

	hr_settings = frappe.get_doc("HR Settings")
	hr_settings.birthday_email_template = _("Birthday Email Notification")
	hr_settings.save()
