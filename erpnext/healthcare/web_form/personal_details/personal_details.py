import frappe
from frappe import _

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.throw(_("You need to be logged in to access this page"), frappe.PermissionError)

	context.show_sidebar = True

	if frappe.db.exists("Patient", {"email": frappe.session.user}):
		patient = frappe.get_doc("Patient", {"email": frappe.session.user})
		context.doc = patient
		frappe.form_dict.new = 0
		frappe.form_dict.name = patient.name


def get_patient():
	return frappe.get_value("Patient", {"email": frappe.session.user}, "name")


def has_website_permission(doc, ptype, user, verbose=False):
	if doc.name == get_patient():
		return True
	else:
		return False
