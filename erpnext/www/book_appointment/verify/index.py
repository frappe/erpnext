import frappe
from frappe.utils.verified_command import verify_request


def get_context(context):
	if not verify_request():
		context.success = False
		return context

	email = frappe.form_dict["email"]
	appointment_name = frappe.form_dict["appointment"]

	if email and appointment_name:
		appointment = frappe.get_doc("Appointment", appointment_name)
		appointment.set_verified(email)
		context.success = True
		return context
	else:
		context.success = False
		return context
