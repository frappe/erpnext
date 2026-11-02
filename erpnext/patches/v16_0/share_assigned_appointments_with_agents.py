import json

import frappe
from frappe.share import add_docshare


def execute():
	"""Share assigned appointments with agents who could read them only before Employee access became owner-only."""
	users = set(frappe.get_all("User", pluck="name"))
	appointments = frappe.get_all(
		"Appointment", filters={"_assign": ("is", "set")}, fields=["name", "_assign"]
	)
	for appointment in appointments:
		for agent in json.loads(appointment._assign or "[]"):
			if agent in users and not frappe.has_permission("Appointment", doc=appointment.name, user=agent):
				add_docshare("Appointment", appointment.name, agent, flags={"ignore_share_permission": True})
