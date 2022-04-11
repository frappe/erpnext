import frappe

import erpnext.education.utils as utils

no_cache = 1


def get_context(context):
	context.education_settings = frappe.get_single("Education Settings")
	if not context.education_settings.enable_lms:
		frappe.local.flags.redirect_location = "/"
		raise frappe.Redirect
	context.featured_programs = get_featured_programs()


def get_featured_programs():
	return utils.get_portal_programs() or []
