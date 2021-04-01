from __future__ import unicode_literals
from frappe import _
import frappe

def execute():
	hr_settings = frappe.get_single("HR Settings")
	hr_settings.leave_approval_notification_template = _("Leave Approval Notification")
	hr_settings.leave_status_notification_template = _("Leave Status Notification")
	hr_settings.save()
