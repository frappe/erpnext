import frappe
from frappe import _
from frappe.utils import get_datetime, now_datetime
from frappe.utils.verified_command import verify_request


def get_context(context):
	if not verify_request():
		context.success = False
		return context

	email = frappe.form_dict["email"]
	appointment_name = frappe.form_dict["appointment"]
	valid_till = frappe.form_dict.get("valid_till")

	if not (email and appointment_name):
		context.success = False
		return context

	if not valid_till or get_datetime(valid_till) < now_datetime():
		context.success = False
		context.message = _("Verification link has expired.")
		return context

	if not frappe.db.exists("Appointment", appointment_name):
		context.success = False
		context.message = _("Appointment not found. Please book the appointment again.")
		return context

	appointment = frappe.get_doc("Appointment", appointment_name)

	if appointment.customer_email != email:
		context.success = False
		context.message = _("Email couldn't be verified.")
		return context

	if appointment.status == "Closed":
		context.success = False
		context.message = _("Appointment has been closed. Please book the appointment again.")
		return context

	if appointment.status == "Open":
		context.success = True
		context.message = _("Appointment is already verified.")
		return context

	verify_appointment(appointment)
	# GET requests are rolled back at the end of the request unless this flag is set
	frappe.local.flags.commit = True
	context.success = True
	return context


def verify_appointment(appointment):
	# the signed link is the authorization; materializing the appointment
	# (agent assignment) needs system privileges the Guest visitor lacks
	visitor = frappe.session.user
	try:
		frappe.set_user("Administrator")
		appointment.email_verified = True
		appointment.status = "Open"
		appointment.save(ignore_permissions=True)
	finally:
		frappe.set_user(visitor)
