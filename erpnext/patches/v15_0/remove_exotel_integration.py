from contextlib import suppress

import click
import frappe
from frappe import _
from frappe.desk.doctype.notification_log.notification_log import make_notification_logs
from frappe.utils.user import get_system_managers

SETTINGS_DOCTYPE = "Exotel Settings"


def execute():
	if "exotel_integration" in frappe.get_installed_apps():
		return

	with suppress(Exception):
		exotel = frappe.get_doc(SETTINGS_DOCTYPE)
		if exotel.enabled:
			notify_existing_users()

		frappe.delete_doc("DocType", SETTINGS_DOCTYPE)


def notify_existing_users():
	click.secho(
		"Exotel integration is moved to a separate app and will be removed from ERPNext in version-15.\n"
		"Please install the app to continue using the integration: https://github.com/frappe/exotel_integration",
		fg="yellow",
	)

	notification = {
		"subject": _(
			"WARNING: Exotel app has been separated from ERPNext, please install the app to continue using Exotel integration."
		),
		"type": "Alert",
	}
	make_notification_logs(notification, get_system_managers(only_name=True))
