from __future__ import unicode_literals
import erpnext.education.utils as utils
import frappe

no_cache = 1

def get_context(context):
	context.education_settings = frappe.get_single("Education Settings")
	context.all_programs = get_all_programs()

def get_all_programs():
	program_names = frappe.get_all("Program", filters={"is_published": True})
	if program_names:
		program_list = [utils.get_program_and_enrollment_status(program['name']) for program in program_names]
		return program_list
