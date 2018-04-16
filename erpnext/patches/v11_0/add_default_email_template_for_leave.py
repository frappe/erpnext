import frappe
from frappe import _

def execute():
	frappe.reload_doc("setup", "doctype", "email_template")

	if not frappe.db.exists("Email Template", _('Leave Approval Notification')):
		name = "Leave Approval Notification"
		response = frappe.render_template("erpnext/hr/doctype/leave_application/leave_application_email_template.html",{'data': name})
		frappe.get_doc({
			'doctype': 'Email Template',
			'name': name,
			'response': response,
			'subject': name,
			"owner": frappe.session.user,
		}).insert(ignore_permissions=True)


	if not frappe.db.exists("Email Template", _('Leave Status Notification')):
		name = "Leave Status Notification"
		response = frappe.render_template("erpnext/hr/doctype/leave_application/leave_application_email_template.html",{'data': name})
		frappe.get_doc({
			'doctype': 'Email Template',
			'name': name,
			'response': response,
			'subject': name,
			"owner": frappe.session.user,
		}).insert(ignore_permissions=True)

