import os

import frappe
from frappe import _


def execute():
	frappe.reload_doc("email", "doctype", "email_template")
	frappe.reload_doc("stock", "doctype", "delivery_settings")

	if not frappe.db.exists("Email Template", _("Dispatch Notification")):
		base_path = frappe.get_app_path("erpnext", "stock", "doctype")
		response = frappe.read_file(
			os.path.join(base_path, "delivery_trip/dispatch_notification_template.html")
		)

		frappe.get_doc(
			{
				"doctype": "Email Template",
				"name": _("Dispatch Notification"),
				"response": response,
				"subject": _("Your order is out for delivery!"),
				"owner": frappe.session.user,
			}
		).insert(ignore_permissions=True)

	delivery_settings = frappe.get_doc("Delivery Settings")
	delivery_settings.dispatch_template = _("Dispatch Notification")
	delivery_settings.flags.ignore_links = True
	delivery_settings.save()
