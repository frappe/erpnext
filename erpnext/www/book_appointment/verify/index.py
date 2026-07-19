import frappe
from frappe.utils.verified_command import verify_request


def get_context(context):
	if not verify_request():
		context.success = False
		return context

	email = frappe.form_dict["email"]
	appointment_name = frappe.form_dict["appointment"]

	if not (email and appointment_name):
		context.success = False
		return context

	appointment = frappe.get_doc("Appointment", appointment_name)

	if appointment.status != "Unverified":
		context.success = True
		return context

	appointment.set_verified(email)
	appointment.save(ignore_permissions=True)
	# GET requests are rolled back at the end of the request unless this flag is set
	frappe.local.flags.commit = True
	context.success = True
	return context
