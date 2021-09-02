from __future__ import unicode_literals

import os

import frappe
from frappe import _


def execute():
	frappe.reload_doc("email", "doctype", "email_template")

	if not frappe.db.exists("Email Template", _('Leave Approval Notification')):
		base_path = frappe.get_app_path("erpnext", "hr", "doctype")
		response = frappe.read_file(os.path.join(base_path, "leave_application/leave_application_email_template.html"))
		frappe.get_doc({
			'doctype': 'Email Template',
			'name': _("Leave Approval Notification"),
			'response': response,
			'subject': _("Leave Approval Notification"),
			'owner': frappe.session.user,
		}).insert(ignore_permissions=True)


	if not frappe.db.exists("Email Template", _('Leave Status Notification')):
		base_path = frappe.get_app_path("erpnext", "hr", "doctype")
		response = frappe.read_file(os.path.join(base_path, "leave_application/leave_application_email_template.html"))
		frappe.get_doc({
			'doctype': 'Email Template',
			'name': _("Leave Status Notification"),
			'response': response,
			'subject': _("Leave Status Notification"),
			'owner': frappe.session.user,
		}).insert(ignore_permissions=True)
