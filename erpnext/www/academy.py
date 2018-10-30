from __future__ import unicode_literals
import frappe
import erpnext.education.utils as utils

@frappe.whitelist()
def get_portal_details():
	settings = frappe.get_doc("Education Settings")
	title = settings.portal_title
	description = settings.description
	return dict(title=title, description=description)

@frappe.whitelist()
def get_featured_programs():
	featured_program_names = frappe.get_list("Program", filters={"is_published": True, "is_featured": True})
	featured_list = [program["name"] for program in featured_program_names]
	if featured_list:
		return featured_list
	else:
		return None

@frappe.whitelist()
def get_program_details(program_name):
	try:
		program = frappe.get_doc('Program', program_name)
		return program
	except:
		return None
