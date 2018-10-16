from __future__ import unicode_literals
import erpnext.education.utils as utils
import frappe


def get_context(context):
    context.program = frappe.get_doc("Program", frappe.form_dict["program"])
    context.course_list = utils.get_courses_in_program(frappe.form_dict["program"])