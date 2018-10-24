from __future__ import unicode_literals
import erpnext.education.utils as utils
import frappe


def get_context(context):
    program = frappe.get_doc("Program", frappe.form_dict["program"])
    course_list = program.get_course_list()

    context.program = program
    context.course_list = course_list
    context.check_complete = check_complete


def check_complete(course_name):
	try:
		enrollment = utils.get_course_enrollment(course_name, frappe.session.user)
		completed = frappe.get_value('Course Enrollment', enrollment['name'], "completed")
		return bool(completed)
	except:
		return False