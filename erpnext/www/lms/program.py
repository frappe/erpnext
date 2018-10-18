from __future__ import unicode_literals
import erpnext.education.utils as utils
import frappe


def get_context(context):
    program = frappe.get_doc("Program", frappe.form_dict["program"])
    course_list = program.get_course_list()

    context.program = program
    context.course_list = course_list