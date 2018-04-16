import frappe
from frappe import _

def execute():
	frappe.reload_doc("setup", "doctype", "email_template")

	if not frappe.db.exists("Email Template", _('Leave Approval Notification')):
		frappe.get_doc({
			'doctype': 'Email Template',
			'name': _('Leave Approval Notification'),
			'response': _('Leave Approval Notification <br><br>\
			- Leave Application: {{name}} <br>\
			- Employee: {{employee_name}} <br>\
			- Leave Type: {{leave_type}} <br>\
			- From Date: {{from_date}} <br>\
			- To Date: {{to_date}} <br>\
			- Status: {{status}}'),
			'subject': _('Leave Approval Notification'),
			"owner": frappe.session.user,
		}).insert(ignore_permissions=True)

	if not frappe.db.exists("Email Template", _('Leave Status Notification')):
		frappe.get_doc({
			'doctype': 'Email Template',
			'name': _('Leave Status Notification'),
			'response': _(
				'Leave Status Notification <br><br>\
				- Leave Application: {{name}} <br>\
				- Employee: {{employee_name}} <br>\
				- Leave Type: {{leave_type}} <br>\
				- From Date: {{from_date}} <br>\
				- To Date: {{to_date}} <br>\
				- Status: {{status}}'),
			'subject': _('Leave Status Notification'),
			"owner": frappe.session.user,
		}).insert(ignore_permissions=True)
