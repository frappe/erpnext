from __future__ import unicode_literals
import erpnext.education.utils as utils
import frappe

no_cache = 1

def get_context(context):
	context.education_settings = frappe.get_single("Education Settings")
	if not context.education_settings.enable_lms:
		frappe.local.flags.redirect_location = '/'
		raise frappe.Redirect
	context.featured_programs = get_featured_programs()


def get_featured_programs():
	featured_program_names = frappe.get_all("Program", filters={"is_published": True, "is_featured": True})
	if featured_program_names:
		featured_list = [utils.get_program_and_enrollment_status(program['name']) for program in featured_program_names]
		return featured_list
	else:
		return get_all_programs()[:2]

def get_all_programs():
	program_names = frappe.get_all("Program", filters={"is_published": True})
	if program_names:
		program_list = [utils.get_program_and_enrollment_status(program['name']) for program in program_names]
		return program_list
