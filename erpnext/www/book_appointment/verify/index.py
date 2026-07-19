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

	# Expired Unverified appointments are deleted by the scheduled cleanup job,
	# so a signed link can outlive its appointment.
	if not frappe.db.exists("Appointment", appointment_name):
		context.success = False
		context.message = _("Verification link has expired. Please book the appointment again.")
		return context

	appointment = frappe.get_doc("Appointment", appointment_name)

	if appointment.status != "Unverified":
		context.success = True
		return context

	if not valid_till or get_datetime(valid_till) < now_datetime():
		context.success = False
		context.message = _("Verification link has expired. Please book the appointment again.")
		return context

	appointment.set_verified(email)
	appointment.save(ignore_permissions=True)
	# GET requests are rolled back at the end of the request unless this flag is set
	frappe.local.flags.commit = True
	context.success = True
	return context
