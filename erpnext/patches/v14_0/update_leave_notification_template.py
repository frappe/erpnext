import os

import frappe
from frappe import _


def execute():
	base_path = frappe.get_app_path("erpnext", "hr", "doctype")
	response = frappe.read_file(
		os.path.join(base_path, "leave_application/leave_application_email_template.html")
	)

	template = frappe.db.exists("Email Template", _("Leave Approval Notification"))
	if template:
		frappe.db.set_value("Email Template", template, "response", response)

	template = frappe.db.exists("Email Template", _("Leave Status Notification"))
	if template:
		frappe.db.set_value("Email Template", template, "response", response)
