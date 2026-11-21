import frappe
from frappe.share import add_docshare


def execute():
	"""Share assigned appointments with agents who could read them only before Employee access became owner-only."""
	users = set(frappe.get_all("User", pluck="name"))
	# closed ToDos drop out of _assign, so read the agents from the ToDos themselves
	assignments = frappe.get_all(
		"ToDo",
		filters={"reference_type": "Appointment", "status": ("!=", "Cancelled")},
		fields=["reference_name", "allocated_to"],
		distinct=True,
	)
	for assignment in assignments:
		appointment, agent = assignment.reference_name, assignment.allocated_to
		if agent in users and not frappe.has_permission("Appointment", doc=appointment, user=agent):
			add_docshare("Appointment", appointment, agent, flags={"ignore_share_permission": True})
